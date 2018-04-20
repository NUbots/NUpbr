#!C:\"Program Files"\"Blender Foundation"\Blender\blender -P

import os
import bpy
import mathutils
import sys

# TODO: Remove hacky include
# Add our current position to path to include our config files
sys.path.insert(0, '.')
sys.path.insert(0, '../field_uv_generation/')

import field_config as field_cfg
import blend_config as blend_cfg

# Clear environment of all objects
def clear_env():
    for obj in bpy.data.objects:
        if obj.name != 'Camera':
            bpy.data.objects.remove(obj)

# Setup our render parameters
def setup_render():
    # Alias render config
    rend_cfg = blend_cfg.render
    scene_cfg = blend_cfg.scene

    context = bpy.context
    scene = bpy.data.scenes['Scene']

    # Set unit settings
    scene.unit_settings.system = scene_cfg['units']['length_units']
    scene.unit_settings.system_rotation = scene_cfg['units']['rotation_units']

    # Set render settings
    # Cycles rendering and establish our scene
    bpy.context.scene.render.engine = rend_cfg['render_engine']

    # Set render submenu settings
    scene.cycles.device = rend_cfg['render']['cycles_device']

    # Set dimensions settings
    [scene.render.resolution_x, scene.render.resolution_y] = rend_cfg['dimensions']['resolution']
    scene.render.resolution_percentage = rend_cfg['dimensions']['percentage']

    # Set sampling settings
    scene.cycles.samples = rend_cfg['sampling']['cycles_samples']
    scene.cycles.preview_samples = rend_cfg['sampling']['cycles_preview_samples']

    # Set light paths settings
    scene.cycles.transparent_max_bounces = rend_cfg['light_paths']['transparency']['max_bounces']
    scene.cycles.transparent_min_bounces = rend_cfg['light_paths']['transparency']['min_bounces']
    scene.cycles.max_bounces = rend_cfg['light_paths']['bounces']['max_bounces']
    scene.cycles.min_bounces = rend_cfg['light_paths']['bounces']['min_bounces']
    scene.cycles.diffuse_bounces = rend_cfg['light_paths']['diffuse']
    scene.cycles.glossy_bounces = rend_cfg['light_paths']['glossy']
    scene.cycles.transmission_bounces = rend_cfg['light_paths']['transmission']
    scene.cycles.volume_bounces = rend_cfg['light_paths']['volume']
    scene.cycles.caustics_reflective = rend_cfg['light_paths']['reflective_caustics']
    scene.cycles.caustics_refractive = rend_cfg['light_paths']['refractive_caustics']

    # Object indexing for segmentation
    scene.render.layers['RenderLayer'].use_pass_object_index = True
    scene.use_nodes = True

    # Set performance Settings
    [context.scene.render.tile_x, context.scene.render.tile_y] = rend_cfg['performance']['render_tile']

    # Disable splash screen
    context.user_preferences.view.show_splash = False

# Create material for the field
def create_field_mat(f_object, m_cfg):
    # print(dir(bpy.data.materials))
    f_mat = bpy.data.materials.new('Field_Mat')
    # print(dir(f_mat))
    # Enable use of material nodes
    f_mat.use_nodes = True

    # Get our node list to construct our material
    node_list = f_mat.node_tree.nodes

    # Clear node tree of default settings
    for node in node_list:
        node_list.remove(node)

    # Construct node tree
    # Get texture and object coordinates from object
    n_tex_coord = node_list.new('ShaderNodeTexCoord')
    n_tex_coord.object = f_object

    # Create mapping to transform object coordinates for grass height
    n_mapping = node_list.new('ShaderNodeMapping')
    n_mapping.translation = m_cfg['mapping']['translation']
    n_mapping.rotation = m_cfg['mapping']['rotation']
    n_mapping.scale = m_cfg['mapping']['scale']

    # Create gradient texture to transform our mapping into RGB gradient
    n_grad_tex = node_list.new('ShaderNodeTexGradient')
    # Create RGB mixer to produce lower grass colours (earth/green)
    n_mix_lower_grass = node_list.new('ShaderNodeMixRGB')
    n_mix_lower_grass.inputs[1].default_value = m_cfg['mix_lower_grass']['inp1']
    n_mix_lower_grass.inputs[2].default_value = m_cfg['mix_lower_grass']['inp2']

    # Create RGB mixer to produce upper grass colours (light green/yellow)
    n_mix_upper_grass = node_list.new('ShaderNodeMixRGB')
    n_mix_upper_grass.inputs[1].default_value = m_cfg['mix_upper_grass']['inp1']
    n_mix_upper_grass.inputs[2].default_value = m_cfg['mix_upper_grass']['inp2']

    # Create noise texture to give random variance to top colour
    n_noise_tex = node_list.new('ShaderNodeTexNoise')
    [
        n_noise_tex.inputs[1].default_value,
        n_noise_tex.inputs[2].default_value,
        n_noise_tex.inputs[3].default_value,
    ] = m_cfg['noise']['inp']

    # Create Hue Saturation Value shader to transform noise into tone noise exclusively
    n_hsv = node_list.new('ShaderNodeHueSaturation')
    [
        n_hsv.inputs[0].default_value,
        n_hsv.inputs[1].default_value,
        n_hsv.inputs[2].default_value,
        n_hsv.inputs[3].default_value,
    ] = m_cfg['hsv']['inp']

    # Mix RGB colour of upper grass with generated noise
    n_mix_up_grass_hsv = node_list.new('ShaderNodeMixRGB')
    n_mix_up_grass_hsv.inputs[0].default_value = m_cfg['mix_up_grass_hsv']['inp0']

    # Create texture image of field UV map
    n_field_lines = node_list.new('ShaderNodeTexImage')
    img_path = os.path.join(field_cfg.image['path'], field_cfg.image['name'] + field_cfg.image['type'])
    try:
        img = bpy.data.images.load(img_path)
    except:
        raise NameError('Cannot load image {0}'.format(img_path))
    n_field_lines.image = img

    n_mix_low_grass_field_lines = node_list.new('ShaderNodeMixRGB')
    n_mix_low_grass_field_lines.inputs[0].default_value = m_cfg['mix_low_grass_field_lines']['inp0']

    n_ao = node_list.new('ShaderNodeAmbientOcclusion')
    n_translucent = node_list.new('ShaderNodeBsdfTranslucent')
    n_mix_ao_transluc = node_list.new('ShaderNodeMixShader')
    n_mix_ao_transluc.inputs[0].default_value = m_cfg['mix_ao_transluc']['inp0']

    n_diffuse = node_list.new('ShaderNodeBsdfDiffuse')

    n_mix_shaders = node_list.new('ShaderNodeMixShader')
    n_mix_shaders.inputs[0].default_value = m_cfg['mix_shaders']['inp0']

    n_output = node_list.new('ShaderNodeOutputMaterial')

    # Link shaders
    tl = f_mat.node_tree.links

    # Link texture coordinates
    tl.new(n_tex_coord.outputs['UV'], n_field_lines.inputs[0])
    tl.new(n_tex_coord.outputs['Object'], n_mapping.inputs[0])

    # Link image texture (field lines uv map)
    tl.new(n_field_lines.outputs['Color'], n_mix_low_grass_field_lines.inputs['Color1'])

    # Link Mapping
    tl.new(n_mapping.outputs[0], n_grad_tex.inputs[0])

    # Link gradient texture
    tl.new(n_grad_tex.outputs[1], n_mix_lower_grass.inputs[0])
    tl.new(n_grad_tex.outputs[1], n_mix_upper_grass.inputs[0])

    # Link noise texture
    tl.new(n_noise_tex.outputs[0], n_hsv.inputs[4])

    # Link lower grass mix
    tl.new(n_mix_lower_grass.outputs[0], n_mix_low_grass_field_lines.inputs['Color2'])
    tl.new(n_mix_lower_grass.outputs[0], n_ao.inputs[0])

    # Link upper grass mix
    tl.new(n_mix_upper_grass.outputs[0], n_mix_up_grass_hsv.inputs[1])

    # Link hsv
    tl.new(n_hsv.outputs[0], n_mix_up_grass_hsv.inputs[2])

    # Link translucent
    tl.new(n_mix_up_grass_hsv.outputs[0], n_translucent.inputs[0])

    # Link field uv and lower grass mix
    tl.new(n_mix_low_grass_field_lines.outputs[0], n_diffuse.inputs[0])

    # Link ao
    tl.new(n_ao.outputs[0], n_mix_ao_transluc.inputs[1])

    # Link translucent
    tl.new(n_translucent.outputs[0], n_mix_ao_transluc.inputs[2])

    # Link shaders
    tl.new(n_diffuse.outputs[0], n_mix_shaders.inputs[1])
    tl.new(n_mix_ao_transluc.outputs[0], n_mix_shaders.inputs[2])

    # Link output
    tl.new(n_mix_shaders.outputs[0], n_output.inputs[0])

    return f_mat

# Create noise texture for grass length variation
def generate_field_noise(n_cfg):
    # Add our noise texture
    bpy.ops.texture.new()
    noise_tex = bpy.data.textures.new('Noise', type=n_cfg['type'])
    # Configure noise parameters
    noise_tex.type = n_cfg['type']
    noise_tex.contrast = n_cfg['contrast']
    noise_tex.noise_scale = n_cfg['noise_scale']
    noise_tex.nabla = n_cfg['nabla']
    return noise_tex

# Construct particle system with p_settings, given p_cfg config file
def construct_particle_system(p_cfg, p_settings):
    # Set general particle settings
    p_settings.type = p_cfg['type']
    p_settings.use_advanced_hair = p_cfg['use_adv_hair']

    # Set emission settings
    p_settings.count = p_cfg['emission']['count']
    p_settings.hair_length = p_cfg['emission']['hair_length']
    p_settings.emit_from = p_cfg['emission']['emit_from']
    p_settings.use_emit_random = p_cfg['emission']['emit_random']
    p_settings.use_even_distribution = p_cfg['emission']['even_dist']

    # Set physics settings
    p_settings.physics_type = p_cfg['physics']['type']
    p_settings.brownian_factor = p_cfg['physics']['brownian_factor']
    p_settings.timestep = p_cfg['physics']['timestep']
    p_settings.subframes = p_cfg['physics']['subframes']

    # Set hair render settings
    p_settings.use_render_emitter = p_cfg['render']['emitter']
    p_settings.use_parent_particles = p_cfg['render']['parents']

    # Set children settings
    p_settings.child_type = p_cfg['children']['child_type']
    p_settings.child_nbr = p_cfg['children']['child_num']
    p_settings.rendered_child_count = p_cfg['children']['rendered_children']
    p_settings.child_length = p_cfg['children']['length']

    # Set cycles hair settings
    p_settings.cycles.shape = p_cfg['cycles_hair']['shape']
    p_settings.cycles.root_width = p_cfg['cycles_hair']['root']
    p_settings.cycles.tip_width = p_cfg['cycles_hair']['tip']
    p_settings.cycles.radius_scale = p_cfg['cycles_hair']['scaling']
    p_settings.cycles.use_closetip = p_cfg['cycles_hair']['close_tip']

# Setup field object
def construct_field():
    # Add plane for field
    bpy.ops.mesh.primitive_plane_add()
    field = bpy.data.objects['Plane']
    field.name = 'Field'

    # Define location and dimensions of field
    field.location = (0, 0, 0)
    field.dimensions = (
        2. * field_cfg.field['border_width'] + field_cfg.field['length'],
        2. * field_cfg.field['border_width'] + field_cfg.field['width'],
        0.,
    )

    # Add material to field material slots
    field.data.materials.append(create_field_mat(field, blend_cfg.field['material']))

    # Define the particle system for grass
    bpy.ops.object.particle_system_add()
    field.particle_systems['ParticleSystem'].name = 'Grass'
    field_particle = field.particle_systems['Grass']

    # Set particle settings
    p_cfg = blend_cfg.field['particle']
    p_settings = field_particle.settings

    # Construct our particle settings for grass
    construct_particle_system(p_cfg, p_settings)

    # Generate our noise texture and link it to the grass
    noise_tex_slot = p_settings.texture_slots.add()
    noise_tex_slot.texture = generate_field_noise(blend_cfg.field['noise'])

    # Adjust impact of texture on grass now that the two are linked
    noise_tex_slot.texture_coords = blend_cfg.field['noise']['mapping_coords']
    noise_tex_slot.use_map_length = blend_cfg.field['noise']['influence']['use_hair_length']
    noise_tex_slot.length_factor = blend_cfg.field['noise']['influence']['hair_length_factor']

    # Apply UV mapping to grass
    bpy.ops.uv.smart_project()

def main():
    # Change directories so we are where this file is
    script_dir = os.path.dirname(os.path.realpath(__file__))

    # Clear default environment
    clear_env()
    # Setup render settings
    setup_render()

    # Construct our grass field
    construct_field()

    # Construct our ball
    # construct_ball()

    # Construct pbr skybox
    # construct_bg()

if __name__ == '__main__':
    main()
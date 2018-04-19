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

# # Setup field object
def construct_field():
    # Add plane for field
    bpy.ops.mesh.primitive_plane_add()
    field = bpy.data.objects['Plane']
    field.name = 'Field'

    # Define location
    field.location = (0, 0, 0)

    # Select our field object
    field.select = True
    bpy.context.scene.objects.active = field

    # Define dimensions from config
    field.dimensions = (
        2. * field_cfg.field['border_width'] + field_cfg.field['length'],
        2. * field_cfg.field['border_width'] + field_cfg.field['width'],
        0.,
    )

    # Create the particle system for grass
    bpy.ops.object.particle_system_add()
    field.particle_systems['ParticleSystem'].name = 'Grass'
    field_particle = field.particle_systems['Grass']

    # Set particle settings
    p_cfg = blend_cfg.field['particle']
    p_settings = field_particle.settings

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
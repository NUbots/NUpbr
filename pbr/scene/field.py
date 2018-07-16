#!/usr/local/blender -P

import os
import bpy

from config import scene_config as scene_cfg
from config import blend_config as blend_cfg

from scene.blender_object import BlenderObject


class Field(BlenderObject):
    def __init__(self, class_index):
        self.loc = (0., 0., 0.)
        self.mat = None
        self.obj = None
        self.pass_index = class_index
        self.construct()

    # Setup field object
    def construct(self):
        # Add plane for field
        bpy.ops.mesh.primitive_plane_add()
        lower_plane = bpy.data.objects['Plane']
        lower_plane.name = 'Lower_Plane'
        lower_plane.pass_index = self.pass_index

        # Define location and dimensions of field
        lower_plane.location = (0, 0, 0)
        lower_plane.dimensions = (
            2. * scene_cfg.field['border_width'] + scene_cfg.field['length'],
            2. * scene_cfg.field['border_width'] + scene_cfg.field['width'],
            0.,
        )

        lower_plane.data.materials.append(
            self.create_lower_plane_mat(blend_cfg.field['lower_plane']))

        # Apply UV mapping to grass
        bpy.ops.uv.smart_project()

        # Add plane for field
        bpy.ops.mesh.primitive_plane_add()
        field = bpy.data.objects['Plane']
        field.name = 'Field'
        field.pass_index = self.pass_index

        # Define location and dimensions of field
        field.location = (0, 0, 0)
        field.dimensions = (
            2. * scene_cfg.field['border_width'] + scene_cfg.field['length'],
            2. * scene_cfg.field['border_width'] + scene_cfg.field['width'],
            0.,
        )

        # Add material to field material slots
        field.data.materials.append(
            self.create_field_mat(field, blend_cfg.field['material']))

        # Define the particle system for grass
        bpy.ops.object.particle_system_add()
        field.particle_systems['ParticleSystem'].name = 'Grass'
        field_particle = field.particle_systems['Grass']

        # Set particle settings
        p_cfg = blend_cfg.field['particle']
        p_settings = field_particle.settings

        # Construct our particle settings for grass
        self.construct_particle_system(p_cfg, p_settings)

        # Generate our noise texture and link it to the grass
        noise_tex_slot = p_settings.texture_slots.add()
        noise_tex_slot.texture = self.generate_field_noise(
            blend_cfg.field['noise'])

        # Adjust impact of texture on grass now that the two are linked
        noise_tex_slot.texture_coords = blend_cfg.field['noise'][
            'mapping_coords']
        noise_tex_slot.use_map_length = blend_cfg.field['noise']['influence'][
            'use_hair_length']
        noise_tex_slot.length_factor = blend_cfg.field['noise']['influence'][
            'hair_length_factor']

        # Apply UV mapping to grass
        bpy.ops.uv.smart_project()

    # Create material for the lower plane
    def create_lower_plane_mat(self, p_cfg):
        lp_mat = bpy.data.materials.new('Lower_Plane_Mat')
        # Enable use of material nodes
        lp_mat.use_nodes = True

        # Get our node list to construct our material
        node_list = lp_mat.node_tree.nodes

        # Clear node tree of default settings
        for node in node_list:
            node_list.remove(node)

        # Create RGB, principled and output nodes
        n_rgb = node_list.new('ShaderNodeRGB')
        n_rgb.outputs[0].default_value = p_cfg['colour']

        n_princ = node_list.new('ShaderNodeBsdfPrincipled')
        n_princ.inputs[5].default_value = p_cfg['specular']
        n_princ.inputs[7].default_value = p_cfg['roughness']

        n_output = node_list.new('ShaderNodeOutputMaterial')

        # Link shaders
        tl = lp_mat.node_tree.links
        tl.new(n_rgb.outputs[0], n_princ.inputs[0])
        tl.new(n_princ.outputs[0], n_output.inputs[0])

        return lp_mat

    # Create material for the field
    def create_field_mat(self, f_object, m_cfg):
        f_mat = bpy.data.materials.new('Field_Mat')
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
        n_mix_lower_grass.inputs[1].default_value = m_cfg['mix_lower_grass'][
            'inp1']
        n_mix_lower_grass.inputs[2].default_value = m_cfg['mix_lower_grass'][
            'inp2']

        # Create RGB mixer to produce upper grass colours (light green/yellow)
        n_mix_upper_grass = node_list.new('ShaderNodeMixRGB')
        n_mix_upper_grass.inputs[1].default_value = m_cfg['mix_upper_grass'][
            'inp1']
        n_mix_upper_grass.inputs[2].default_value = m_cfg['mix_upper_grass'][
            'inp2']

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
        n_mix_up_grass_hsv.inputs[0].default_value = m_cfg['mix_up_grass_hsv'][
            'inp0']

        # Create texture image of field UV map
        n_field_lines = node_list.new('ShaderNodeTexImage')
        img_path = os.path.join(
            scene_cfg.field_uv['uv_path'],
            scene_cfg.field_uv['name'] + scene_cfg.field_uv['type'])
        try:
            img = bpy.data.images.load(img_path)
        except:
            raise NameError('Cannot load image {0}'.format(img_path))
        n_field_lines.image = img

        n_mix_low_grass_field_lines = node_list.new('ShaderNodeMixRGB')
        n_mix_low_grass_field_lines.inputs[0].default_value = m_cfg[
            'mix_low_grass_field_lines']['inp0']

        n_mix_grass = node_list.new('ShaderNodeMixRGB')
        n_mix_grass.inputs[0].default_value = m_cfg['mix_grass']['inp0']

        n_princ = node_list.new('ShaderNodeBsdfPrincipled')
        n_princ.inputs[7].default_value = m_cfg['principled']['roughness']

        n_output = node_list.new('ShaderNodeOutputMaterial')

        # Link shaders
        tl = f_mat.node_tree.links

        # Link texture coordinates
        tl.new(n_tex_coord.outputs['UV'], n_field_lines.inputs[0])
        tl.new(n_tex_coord.outputs['Object'], n_mapping.inputs[0])

        # Link image texture (field lines uv map)
        tl.new(n_field_lines.outputs['Color'],
               n_mix_low_grass_field_lines.inputs['Color1'])

        # Link Mapping
        tl.new(n_mapping.outputs[0], n_grad_tex.inputs[0])

        # Link gradient texture
        tl.new(n_grad_tex.outputs[1], n_mix_lower_grass.inputs[0])
        tl.new(n_grad_tex.outputs[1], n_mix_upper_grass.inputs[0])

        # Link noise texture
        tl.new(n_noise_tex.outputs[0], n_hsv.inputs[4])

        # Link lower grass mix
        tl.new(n_mix_lower_grass.outputs[0],
               n_mix_low_grass_field_lines.inputs['Color2'])

        # Link upper grass mix
        tl.new(n_mix_upper_grass.outputs[0], n_mix_up_grass_hsv.inputs[1])

        # Link hsv
        tl.new(n_hsv.outputs[0], n_mix_up_grass_hsv.inputs[2])

        # Link grass mix
        tl.new(n_mix_low_grass_field_lines.outputs[0], n_mix_grass.inputs[1])
        tl.new(n_mix_up_grass_hsv.outputs[0], n_mix_grass.inputs[2])

        # Link principled
        tl.new(n_mix_grass.outputs[0], n_princ.inputs[0])

        # Link output
        tl.new(n_princ.outputs[0], n_output.inputs[0])

        return f_mat

    # Create noise texture for grass length variation
    def generate_field_noise(self, n_cfg):
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
    def construct_particle_system(self, p_cfg, p_settings):
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
        p_settings.rendered_child_count = p_cfg['children'][
            'rendered_children']
        p_settings.child_length = p_cfg['children']['length']

        # Set cycles hair settings
        p_settings.cycles.shape = p_cfg['cycles_hair']['shape']
        p_settings.cycles.root_width = p_cfg['cycles_hair']['root']
        p_settings.cycles.tip_width = p_cfg['cycles_hair']['tip']
        p_settings.cycles.radius_scale = p_cfg['cycles_hair']['scaling']
        p_settings.cycles.use_closetip = p_cfg['cycles_hair']['close_tip']

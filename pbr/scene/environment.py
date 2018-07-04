#!/usr/local/blender -P

import os
import bpy

from config import scene_config as scene_cfg
from config import blend_config as blend_cfg

# Clear environment of all objects
def clear_env():
    for obj in bpy.data.objects:
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
    context.scene.render.engine = rend_cfg['render_engine']

    # Set render submenu settings
    scene.cycles.device = rend_cfg['render']['cycles_device']

    # Set denoising settings
    context.scene.render.layers[0].cycles.use_denoising = blend_cfg.layers['denoising']['use_denoising']

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

# Setup background HDRI environment
def setup_hdri_env(img_path):
    # Get world
    world = bpy.data.worlds['World']
    world.name = 'World_HDR'
    world.use_nodes = True

    # Get our node list to make material
    node_list = world.node_tree.nodes

    # Load our HDRI image and store in environment texture shader
    n_env_tex = node_list.new('ShaderNodeTexEnvironment')

    # Update the HDRI environment with the texture
    update_hdri_env(world, img_path)

    # Link our nodes
    tl = world.node_tree.links

    # Link texture image
    tl.new(n_env_tex.outputs[0], node_list['Background'].inputs[0])
    # Link background to output
    tl.new(node_list['Background'].outputs[0], node_list['World Output'].inputs[0])

    return world

def update_hdri_env(world, img_path):
    n_env_tex = world.node_tree.nodes['Environment Texture']

    try:
        img = bpy.data.images.load(img_path)
    except:
        raise NameError('Cannot load image {0}'.format(img_path))
    n_env_tex.image = img

def setup_image_seg_mat(total_classes):
    seg_mat = bpy.data.materials.new('Image_Seg')
    # Enable material nodes
    seg_mat.use_nodes = True
    # Get our node list
    node_list = seg_mat.node_tree.nodes

    # Clear nodes
    for node in node_list:
        node_list.remove(node)

    # Create our nodes
    # Create node to get object index
    n_obj_info = node_list.new('ShaderNodeObjectInfo')
    # Create division node
    n_div = node_list.new('ShaderNodeMath')
    n_div.operation = 'DIVIDE'
    n_div.inputs[1].default_value = len(scene_cfg.classes)
    # Create Colour Ramp node
    n_col_ramp = node_list.new('ShaderNodeValToRGB')
    n_col_ramp.color_ramp.interpolation = 'CONSTANT'

    # Iterate through classes and create colour regions in colour ramp for each class
    for obj_class in scene_cfg.classes:
        elem = n_col_ramp.color_ramp.elements.new(
            position=(scene_cfg.classes[obj_class]['index'] / (len(scene_cfg.classes))) - 0.5 /
            (len(scene_cfg.classes))
        )
        elem.color = scene_cfg.classes[obj_class]['colour']

    # Create emission node
    n_emission = node_list.new('ShaderNodeEmission')
    # Create output node
    n_output = node_list.new('ShaderNodeOutputMaterial')

    # Link our shaders
    tl = seg_mat.node_tree.links
    # Link object index to divide node
    tl.new(n_obj_info.outputs[1], n_div.inputs[0])
    # Link divide to colour ramp factor
    tl.new(n_div.outputs[0], n_col_ramp.inputs[0])
    # Link colour ramp output to emission
    tl.new(n_col_ramp.outputs[0], n_emission.inputs[0])
    # Link emission to output
    tl.new(n_emission.outputs[0], n_output.inputs[0])

    return seg_mat

def setup_field_seg_mat(index, total_classes):
    seg_mat = bpy.data.materials.new('Field_Seg')
    # Enable material nodes
    seg_mat.use_nodes = True
    # Get our node list
    node_list = seg_mat.node_tree.nodes

    # Clear nodes
    for node in node_list:
        node_list.remove(node)

    # Create our nodes
    # Create node to get object index
    n_obj_info = node_list.new('ShaderNodeObjectInfo')
    # Create node texture image of field UV map
    n_field_lines = node_list.new('ShaderNodeTexImage')
    img_path = os.path.join(scene_cfg.field_uv['uv_path'], scene_cfg.field_uv['name'] + scene_cfg.field_uv['type'])
    try:
        img = bpy.data.images.load(img_path)
    except:
        raise NameError('Cannot load image {0}'.format(img_path))
    n_field_lines.image = img
    # Create modulo node
    n_mod = node_list.new('ShaderNodeMath')
    n_mod.operation = 'MODULO'
    n_mod.inputs[1].default_value = scene_cfg.classes['field']['index']
    n_mod.use_clamp = True
    # Create subtraction node
    n_sub = node_list.new('ShaderNodeMath')
    n_sub.operation = 'SUBTRACT'
    n_sub.inputs[0].default_value = 1.
    n_sub.use_clamp = True
    # Create holdout node
    n_holdout = node_list.new('ShaderNodeHoldout')
    # Create emission node
    n_emission = node_list.new('ShaderNodeEmission')
    # Mix shader
    n_shaders = node_list.new('ShaderNodeMixShader')
    # Output
    n_output = node_list.new('ShaderNodeOutputMaterial')

    # Link our shaders
    tl = seg_mat.node_tree.links
    # Link obj index to division
    tl.new(n_obj_info.outputs[1], n_mod.inputs[0])
    # Link image strength to emission
    tl.new(n_field_lines.outputs[1], n_emission.inputs[1])
    # Link greater than, holdout, emission to mix shader
    tl.new(n_mod.outputs[0], n_sub.inputs[1])
    tl.new(n_sub.outputs[0], n_shaders.inputs[0])
    tl.new(n_holdout.outputs[0], n_shaders.inputs[1])
    tl.new(n_emission.outputs[0], n_shaders.inputs[2])
    # Link mix shader to output
    tl.new(n_shaders.outputs[0], n_output.inputs[0])

    return seg_mat

def setup_scene_composite(field_line_val, l_image_seg, l_field_seg):
    # Enable compositing nodes
    bpy.context.scene.use_nodes = True
    # Get our node list
    node_list = bpy.context.scene.node_tree.nodes

    # Clear nodes
    for node in node_list:
        node_list.remove(node)

    # Render layer for image segment
    n_img_seg_rl = node_list.new('CompositorNodeRLayers')
    n_img_seg_rl.layer = l_image_seg.name
    # Render layer for field segment
    n_field_seg_rl = node_list.new('CompositorNodeRLayers')
    n_field_seg_rl.layer = l_field_seg.name
    # Color key node
    n_col_key = node_list.new('CompositorNodeColorMatte')
    n_col_key.color_hue = 0.0001
    n_col_key.color_saturation = 0.0001
    n_col_key.color_value = 0.0001
    n_col_key.inputs[1].default_value = (0., 0., 0., 1.)
    # Mix node
    n_mix = node_list.new('CompositorNodeMixRGB')
    n_mix.inputs[2].default_value = scene_cfg.classes['field']['field_lines_colour']
    # Alpha over
    n_alpha = node_list.new('CompositorNodeAlphaOver')
    # Composite
    n_comp = node_list.new('CompositorNodeComposite')

    # Link shaders
    tl = bpy.context.scene.node_tree.links
    # Link image segment render layer
    tl.new(n_img_seg_rl.outputs[0], n_alpha.inputs[1])
    # Link field segment render layer
    tl.new(n_field_seg_rl.outputs[0], n_col_key.inputs[0])
    # Link color key node
    tl.new(n_col_key.outputs[0], n_mix.inputs[1])
    tl.new(n_col_key.outputs[1], n_mix.inputs[0])
    # Link mix to alpha
    tl.new(n_mix.outputs[0], n_alpha.inputs[2])
    # Link alpha to composite
    tl.new(n_alpha.outputs[0], n_comp.inputs[0])

def setup_segmentation_render_layers(num_objects):
    scene = bpy.context.scene
    render_layers = scene.render.layers

    l_image_seg = render_layers.new('Image_Seg')
    l_image_seg.use_sky = False
    l_image_seg.use_strand = blend_cfg.render['layers']['use_hair']
    l_image_seg.samples = 1
    image_seg_mat = setup_image_seg_mat(num_objects)
    l_image_seg.material_override = image_seg_mat

    l_field_seg = render_layers.new('Field_Seg')
    l_field_seg.use_sky = False
    l_field_seg.use_strand = blend_cfg.render['layers']['use_hair']
    l_field_seg.samples = 1
    field_seg_mat = setup_field_seg_mat(num_objects - 1, num_objects)
    l_field_seg.material_override = field_seg_mat

    setup_scene_composite(num_objects / float(num_objects), l_image_seg, l_field_seg)

    return image_seg_mat, field_seg_mat

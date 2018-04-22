#!C:\"Program Files"\"Blender Foundation"\Blender\blender -P

import os
import bpy
import sys
import random as rand

# TODO: Remove hacky include
# Add our current position to path to include our config files
sys.path.insert(0, '.')
sys.path.insert(0, '../field_uv_generation/')

import scene_config as scene_cfg
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
def setup_hdri_env():
    # Get world
    world = bpy.data.worlds['World']
    world.name = 'World_HDR'
    world.use_nodes = True

    # Get our node list to make material
    node_list = world.node_tree.nodes

    # Load our HDRI image and store in environment texture shader
    n_env_tex = node_list.new('ShaderNodeTexEnvironment')
    scene_hdrs = os.listdir(scene_cfg.scene_hdr['path'])
    img_path = os.path.join(scene_cfg.scene_hdr['path'], scene_hdrs[rand.randint(0, len(scene_hdrs) - 1)])
    try:
        img = bpy.data.images.load(img_path)
    except:
        raise NameError('Cannot load image {0}'.format(img_path))
    n_env_tex.image = img

    # Link our nodes
    tl = world.node_tree.links

    # Link texture image
    tl.new(n_env_tex.outputs[0], node_list['Background'].inputs[0])
    # Link background to output
    tl.new(node_list['Background'].outputs[0], node_list['World Output'].inputs[0])
#!/usr/local/bin/blender -P
import bpy
import os
# import bisect
# import math
# import random
# import json

def deleteInitialObjects():
    # Delete the initial cube and lamp objects
    bpy.ops.object.select_by_type(type='MESH')
    bpy.ops.object.delete()
    bpy.ops.object.select_by_type(type='LAMP')
    bpy.ops.object.delete()

def setRenderingEngine(engine='CYCLES', device='CPU', samples=256):
    # Change to the cycles renderer and setup some options
    bpy.context.scene.render.engine = engine
    scene = bpy.data.scenes['Scene']
    scene.cycles.device = device
    scene.cycles.samples = samples

def setRenderResolution(resX=1280, resY=1024, resPercent=100):
    # Set resolution, and render at that resolution
    scene = bpy.data.scenes['Scene']
    scene.render.resolution_x = resX
    scene.render.resolution_y = resY
    scene.render.resolution_percentage = resPercent

##################
# MAIN
##################
# Change directories so we are where this file is
script_dir = os.path.dirname(os.path.realpath(__file__))
# Don't show splash
bpy.context.user_preferences.view.show_splash = False

deleteInitialObjects()
setRenderingEngine(samples=128) # faster render
setRenderResolution()

########################
# Generating grass field
########################

# Set field size
fieldX = 3
fieldY = 3

# get references to needed functions
add_particle = bpy.ops.object.particle_system_add

# add a plane mesh for the grass field
bpy.ops.mesh.primitive_plane_add()
# set field dimensions
field = bpy.data.objects['Plane']
FieldName = 'Field'
field.name = FieldName    # rename plane
field.dimensions = (fieldX, fieldY, 0)
# set the initial location of the field in the workspace
field.location = (0, 0, 0)

# add particle to selected object and the right context
# ensure select
if not field.select:
    field.selected = True
    bpy.context.scene.objects.active = field

# add particle to field
add_particle()
# get the particle
particleName = 'GrassParticles'
field_particle = field.particle_systems
field_particle['ParticleSystem'].name = particleName
field_particle = field_particle[particleName]

# set particle type to hair
particle_settings = field_particle.settings
particle_settings.type = 'HAIR'
# set advance hair particle settings
particle_settings.use_advanced_hair = True
particle_settings.normal_factor = 0.05  # affects the height of hair

particle_settings.factor_random = 0.01  # randomize starting slantness
particle_settings.brownian_factor = 0.1 # amount of random erratic hair movement

particle_settings.child_type = 'INTERPOLATED' # use child particles instead of increasing emission count/number (count property)
particle_settings.roughness_2 = 0.2 # child particle's erratic movement
particle_settings.roughness_2_threshold = 0.2 # amount of child particles not affected by roughness - for "randomness"
particle_settings.roughness_2_size = 1.4 # size of child particle's roughness - higher value, more upright

particle_settings.cycles.shape = 0.05 # cycles shape
particle_settings.cycles.root_width = 0.50 # cycles root thickness
particle_settings.cycles.tip_width = 0.15 # cycles tip width

bpy.data.worlds['World'].light_settings.use_ambient_occlusion = True # enable lighting and shadows?
bpy.data.worlds['World'].light_settings.ao_factor = 0.4 # set lighting factor - affects hair 'lightedness'

# add material to field
bpy.ops.object.material_slot_add()
bpy.ops.material.new()
material = bpy.data.materials['Material.001']
grassMaterialName = 'GrassMaterial'
# field_material_grass = field.active_material
material.name = grassMaterialName
field.material_slots[0].material = material

bpy.ops.object.mode_set(mode='EDIT')        # set field to edit mode
material.use_nodes = True
field_node_tree = material.node_tree        # get the node tree
node_list = field_node_tree.nodes           # iterable list of nodes
node_diffuse = node_list['Diffuse BSDF']    # get diffuse node
node_mat_out = node_list['Material Output'] # get material output node
node_mix_shader = node_list.new('ShaderNodeMixShader')        # add a mix shader node

# TODO: make linking between two nodes into a function
field_node_tree.links.new(node_diffuse.outputs['BSDF'], node_mix_shader.inputs[1]) # link diffuse bsdf and mix shader 1
field_node_tree.links.new(node_mix_shader.outputs['Shader'], node_mat_out.inputs['Surface']) # link mix shader to material output's Surface

# TODO: make unlinking between two nodes into a function
# iterate over links, because links are number indexed, 
# coz im not sure if the index of the new link are the same,
# so search by to_node instead, then delete
for link in node_diffuse.outputs['BSDF'].links:
    if link.to_node.name == 'Material Output':
        field_node_tree.links.remove(link)  # remove the link from diffuse to material output

# add Glossy BSDF shader
node_glossy = node_list.new('ShaderNodeBsdfGlossy')
node_glossy.distribution = 'BECKMANN' # set glossy shader distribution to BECKMANN
field_node_tree.links.new(node_glossy.outputs['BSDF'], node_mix_shader.inputs[2])    # link glossy shader to mix shader 2

# add Texture image shader
node_tex = node_list.new('ShaderNodeTexImage')
turf_file_path = './turf.jpg'
# bpy.ops.image.open(filepath=turf_file_path) # open texture image file
turf_image = bpy.data.images.load(filepath=turf_file_path, check_existing=True)
node_tex.image = turf_image # add the image to image texture node
field_node_tree.links.new(node_tex.outputs['Color'], node_mat_out.inputs['Displacement']) # link texture image and material output nodes
field_node_tree.links.new(node_tex.outputs['Color'], node_diffuse.inputs['Color'])  # link texture image and diffuse nodes

# optional: unwrap the mesh and edit corner points to be the same as the loaded image in image texture node
# have to increase occlusion
# add a sun lamp
bpy.ops.uv.unwrap() # unwrap the mesh to the loaded image # TODO: non bpy.ops of doing this? probably directly to bpy.data

bpy.ops.object.mode_set(mode='OBJECT')        # set field back to object mode
for area in bpy.context.screen.areas:
    print(area.type)
    if area.type == 'VIEW_3D':
        print('area view_3d')
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                print('space view_3d')
                space.viewport_shade = 'RENDERED'
# from here on, we can add another particle system to the field, but of different height
# and add a material for that specific particle system
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

# add a plane mesh for the grass field
bpy.ops.mesh.primitive_plane_add()
# set field dimensions
field = bpy.context.selected_objects[0]
field.dimensions = (fieldX, fieldY, 0)
# set the initial location of the field in the workspace
field.location = (0, 0, 0)
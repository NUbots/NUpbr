#!/usr/local/blender -P

import os
import bpy
import json
import re
from math import radians
from random import triangular

from config import blend_config as blend_cfg
from config import scene_config as scene_cfg

from scene.blender_object import BlenderObject

class Clutter(BlenderObject):
    def __init__(self, name, class_index, clutter_info):
        self.mat = None
        self.pass_index = class_index
        self.objs = {}
        self.name = name
        self.num_objects = 0

    # Setup ball object
    def construct(self, clutter_info):
        robot_mesh = None
        robot_obj = {}

        # Iterate through each clutter object and add to our list of clutter
        for obj_dir in os.listdir(clutter_info["clutter_dir"]):
            # Look through each file to find .fbx or .obj etc
            for f in os.listdir(os.path.join(obj_dir, obj_file)):
                # OBJ
                if re.search(r"*.(OBJ|obj)", f, re.I):
                    self.objs.update({
                        obj_dir: {
                            "dir": os.path.join(obj_dir, obj_file),
                            "obj_file": f,
                        }
                    })
                    bpy.ops.import_scene.obj(filepath=obj_dir[obj_dir]["obj_file"], axis_forward='X', axis_up='Z')
                # FBX
                if re.search(r"*.(FBX|fbx)", f, re.I):
                    self.objs.update({
                        obj_dir: {
                            "dir": os.path.join(obj_dir, obj_file),
                            "obj_file": f,
                        }
                    })
                    bpy.ops.import_scene.fbx(filepath=obj_dir[obj_dir]["obj_file"], axis_forward='X', axis_up='Z')

        self.num_objects = len(self.objs)
        scene_cfg.num_clutter_objects = self.num_objects

    def update(self, cfg):
        for ii in range(self.num_objects):
            self.objs.keys[self.objs.keys()[ii]].location = cfg["position"][ii]
            self.objs.keys[self.objs.keys()[ii]].delta_rotation_euler = cfg["rotation"][ii]

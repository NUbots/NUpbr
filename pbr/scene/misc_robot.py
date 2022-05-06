#!/usr/local/blender -P

import os
import bpy
import json
import re
from math import radians
from random import triangular, randint

from config import blend_config as blend_cfg
from config import scene_config as scene_cfg

from scene.blender_object import BlenderObject


class MiscRobot(BlenderObject):
    def __init__(self, name, class_index, robot_info):
        self.mat = {}
        self.sc_plane = None
        self.robot_parts = None
        self.pass_index = class_index
        self.objs = {}
        self.obj = None
        self.name = name
        self.colour = randint(0, 1)  # 1. white or 0. black
        self.construct(robot_info)

    # Setup robot object
    def construct(self, robot_info):
        robot_mesh = None
        robot_obj = {}
        mesh_path = scene_cfg.new_misc_robot()

        # Load robot object
        bpy.ops.import_scene.fbx(
            filepath= mesh_path, axis_forward="X", axis_up="Z"
        )

        obj = bpy.data.objects["misc_robot"]
        obj.name = "{}".format(self.name)
        self.objs.update({obj.name: obj})
        # Configure robot to have correct pass index
        obj.pass_index = self.pass_index

        # TODO: Make materials not embedded in FBX files
        # Set material for robot
        # self.mat.update({obj.name: self.set_material(obj, "misc_robot_tex")})
        # obj.data.materials.append(self.mat[obj.name])

    def set_material(self, obj, mat_name):
        l_mat = bpy.data.materials.new(mat_name)

        # Enable use of material nodes
        l_mat.use_nodes = True

        # Get our node list to construct our material
        node_list = l_mat.node_tree.nodes

        # Clear node tree of default settings
        for node in node_list:
            node_list.remove(node)

        # Construct node tree
        # Create principled node
        n_principled = node_list.new("ShaderNodeBsdfPrincipled")
        n_principled.inputs["Metallic"].default_value = blend_cfg.misc_robot["material"][
            "metallic"
        ]
        n_principled.inputs["Roughness"].default_value = blend_cfg.misc_robot["material"][
            "roughness"
        ]
        n_principled.inputs[0].default_value = blend_cfg.misc_robot["material"][
            "base_col"
        ]

        # Create output node
        n_output = node_list.new("ShaderNodeOutputMaterial")

        # Link shaders
        tl = l_mat.node_tree.links
        tl.new(n_principled.outputs[0], n_output.inputs[0])

        return l_mat

    def update(self, cfg):
        bpy.data.objects[self.name].location = cfg["position"]
        bpy.data.objects[self.name].delta_rotation_euler = cfg["rotation"]

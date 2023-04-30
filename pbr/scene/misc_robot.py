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
        self.robot = None
        self.robot_parts = None
        self.pass_index = class_index
        self.objs = {}
        self.obj = None
        self.name = name
        self.colour = randint(0, 1)  # 1. white or 0. black
        self.height = 0
        self.construct(robot_info)   

    # Setup robot object
    def construct(self, robot_info):
        robot_mesh = None
        robot_obj = {}

        self.robot = scene_cfg.choose_misc_robot()

        mesh_path = self.robot["mesh_path"]

        self.height = self.robot["height"]

        with open(self.robot["kinematics_path"], "r") as file:
            self.robot_parts = json.loads(file.read())

        bpy.ops.import_scene.fbx(
            filepath=self.robot["mesh_path"], axis_forward="X", axis_up="Z"
        )

        # Pure black is too dark
        if (self.colour == 0):
            self.colour = 0.1

        for p in self.robot_parts.keys():
            obj = bpy.data.objects[p]

            obj.data.materials.clear()

            if obj.parent == None:
                self.obj = obj

            obj.name = "{}_{}".format(self.name, p)
            self.objs.update({obj.name: obj})

            obj.pass_index = self.pass_index

            # Configure robot to have correct pass index
            obj.pass_index = self.pass_index

            # TODO: Make materials not embedded in FBX files
            # Set material for robot
            self.mat.update({obj.name: self.set_material(obj, self.name + "_tex")})
            obj.data.materials.append(self.mat[obj.name])

        self.initialise_kinematics()

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
        n_principled.inputs["Metallic"].default_value = blend_cfg.darwin_robot["material"][
            "metallic"
        ]
        n_principled.inputs["Roughness"].default_value = blend_cfg.darwin_robot["material"][
            "roughness"
        ]
        n_principled.inputs[0].default_value = blend_cfg.darwin_robot["material"][
            "base_col"
        ]

        n_principled.inputs["Base Color"].default_value = (
            self.colour,
            self.colour,
            self.colour,
            1.0,
        )

        # Create output node
        n_output = node_list.new("ShaderNodeOutputMaterial")

        # Link shaders
        tl = l_mat.node_tree.links
        tl.new(n_principled.outputs[0], n_output.inputs[0])
        #tl.new(n_mix_col_map.outputs[0], n_principled.inputs[0])

        return l_mat
    

    def get_height(self):
            return self.height    
    
    def initialise_kinematics(self):
        # Set all joints to neutral pose
        for k in self.robot_parts.keys():
            # Calculate min, max and mode limits
            lim = self.robot_parts[k]["limits"]
            # Calculate delta rotation for the relevant axis
            delta_rot = [0.0, 0.0, 0.0]
            delta_rot[self.robot_parts[k]["rot_axis"]] = radians(lim[1])
            # Add to output dictionary
            bpy.data.objects[
                "{}_{}".format(self.name, k)
            ].delta_rotation_euler = delta_rot

    def update_kinematics(self):
        # Set all joints to neutral pose
        for k in self.robot_parts.keys():
            # Calculate min, max and mode limits
            lim = self.robot_parts[k]["limits"]
            var = self.robot["kinematics_variance"]
            # Calculate delta rotation for the relevant axis
            (v_min, v_max) = (
                lim[1] - var * (lim[1] - lim[0]),
                lim[1] - var * (lim[1] - lim[2]),
            )
            # Calculate delta rotation for the relevant axis
            delta_rot = [0.0, 0.0, 0.0]
            delta_rot[self.robot_parts[k]["rot_axis"]] = radians(
                triangular(v_min, v_max, lim[1])
            )
            # Add to output dictionary
            bpy.data.objects[
                "{}_{}".format(self.name, k)
            ].delta_rotation_euler = delta_rot

    def update(self, cfg):
        self.update_kinematics()
        #Fix this later
        bpy.data.objects[self.name + "_Torso"].location = cfg["position"]
        bpy.data.objects[self.name + "_Torso"].delta_rotation_euler = cfg["rotation"]

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


class Shape(BlenderObject):
    def __init__(self, name, class_index):
        self.mat = None
        self.obj = None
        self.pass_index = class_index
        self.name = name

        self.construct()

    # Setup clutter object
    def construct(self):
        shape_mesh = None
        self.create_obj()
        self.create_mat()

    def create_obj(self):
        mesh = None
        old_objs = list(bpy.data.objects.keys())
        # Create new random shape
        shape_num = randint(1, 7)
        if shape_num == 1:
            mesh = bpy.ops.mesh.primitive_cone_add()
        if shape_num == 2:
            mesh = bpy.ops.mesh.primitive_cube_add()
        if shape_num == 3:
            mesh = bpy.ops.mesh.primitive_cylinder_add()
        if shape_num == 4:
            mesh = bpy.ops.mesh.primitive_grid_add()
        if shape_num == 5:
            mesh = bpy.ops.mesh.primitive_monkey_add()
        if shape_num == 6:
            mesh = bpy.ops.mesh.primitive_plane_add()
        if shape_num == 7:
            mesh = bpy.ops.mesh.primitive_torus_add()
        new_objs = list(bpy.data.objects.keys())
        # Get name of new object to reference
        new_obj_name = [x for x in new_objs if x not in old_objs][0]
        self.obj = bpy.data.objects[new_obj_name]
        self.obj.pass_index = self.pass_index

        # Make ball active object
        bpy.context.view_layer.objects.active = self.obj
        bpy.ops.object.shade_smooth()

        # Rename our created shape
        self.obj.name = self.name

    def create_mat(self):
        b_mat = bpy.data.materials.new(self.name + "_Mat")

        # Enable use of material nodes
        b_mat.use_nodes = True

        # Get our node list to construct our material
        node_list = b_mat.node_tree.nodes

        # Clear node tree of default settings
        for node in node_list:
            node_list.remove(node)

        # Construct node tree
        # Create principled node
        n_principled = node_list.new("ShaderNodeBsdfPrincipled")
        n_principled.inputs[0].default_value = (0.0, 0.0, 0.0, 1.0)

        # Create output node
        n_output = node_list.new("ShaderNodeOutputMaterial")

        # Link shaders
        tl = b_mat.node_tree.links

        # Link Principled to output
        tl.new(n_principled.outputs[0], n_output.inputs[0])

        self.mat = b_mat
        self.obj.data.materials.append(self.mat)

    def set_mat(self, cfg):
        node_list = self.mat.node_tree.nodes

        node_list["Principled BSDF"].inputs[0].default_value = cfg["material"][
            "base_col"
        ][:] + (1.0,)
        node_list["Principled BSDF"].inputs[4].default_value = cfg["material"][
            "metallic"
        ]
        node_list["Principled BSDF"].inputs[7].default_value = cfg["material"][
            "roughness"
        ]

    def update(self, cfg):
        self.obj.location = cfg["position"]
        self.obj.delta_rotation_euler = cfg["rotation"]
        self.obj.dimensions = cfg["dimensions"]
        self.set_mat(cfg)

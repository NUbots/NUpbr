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


class Robot(BlenderObject):
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

    # Setup ball object
    def construct(self, robot_info):
        robot_mesh = None
        robot_obj = {}

        # Load kinematics information
        with open(robot_info["kinematics_path"], "r") as file:
            self.robot_parts = json.loads(file.read())
        # Load robot object
        bpy.ops.import_scene.fbx(
            filepath=robot_info["mesh_path"], axis_forward="X", axis_up="Z"
        )
        # Add object to our list of parts
        for p in self.robot_parts.keys():
            obj = bpy.data.objects[p]
            # Set torso as main robot object
            if obj.parent == None:
                self.obj = obj
            obj.name = "{}_{}".format(self.name, p)
            self.objs.update({obj.name: obj})
            # Configure each part to have correct pass index
            obj.pass_index = self.pass_index

            col_re = r"Base_?Color.*"
            nor_re = r"Normal.*"

            # Use regex to find colour and normal map
            tex_path = os.path.join(
                robot_info["texture_path"], self.robot_parts[p]["dir"]
            )
            col_path = ""
            nor_path = ""
            for file in os.listdir(tex_path):
                if re.search(col_re, file, re.I) is not None:
                    col_path = os.path.join(tex_path, file)
                if re.search(nor_re, file, re.I) is not None:
                    nor_path = os.path.join(tex_path, file)

            # Set material for limb
            self.mat.update({obj.name: self.set_material(obj, p, col_path, nor_path)})
            obj.data.materials.append(self.mat[obj.name])

        self.initialise_kinematics()

    def set_material(self, obj, mat_name, colour_path, normal_path):
        l_mat = bpy.data.materials.new(mat_name)

        # Enable use of material nodes
        l_mat.use_nodes = True

        # Get our node list to construct our material
        node_list = l_mat.node_tree.nodes

        # Clear node tree of default settings
        for node in node_list:
            node_list.remove(node)

        # Construct node tree

        # Create colour texture image of UV map
        n_uv_map = node_list.new("ShaderNodeTexImage")
        n_uv_map.name = "UV_Image"
        try:
            img = bpy.data.images.load(colour_path)
        except:
            raise NameError("Cannot load image {0}".format(colour_path))
        n_uv_map.image = img

        # Create RGB mixer to change base colour of colour map
        n_mix_col_map = node_list.new("ShaderNodeMixRGB")
        n_mix_col_map.inputs[2].default_value = (
            self.colour,
            self.colour,
            self.colour,
            1.0,
        )

        # Create normal map node for texture
        if normal_path is not None:
            n_norm_map = node_list.new("ShaderNodeTexImage")
            n_norm_map.name = "Norm_Map"

            try:
                norm_map = bpy.data.images.load(normal_path)
            except:
                raise NameError("Cannot load image {0}".format(normal_path))
            n_norm_map.image = norm_map
            n_norm_map.image.colorspace_settings.is_data = True
        n_norm_map_conv = node_list.new("ShaderNodeNormalMap")
        n_norm_map_conv.name = "Norm_Map_Conv"

        # Create principled node
        n_principled = node_list.new("ShaderNodeBsdfPrincipled")
        n_principled.inputs["Metallic"].default_value = blend_cfg.robot["material"][
            "metallic"
        ]
        n_principled.inputs["Roughness"].default_value = blend_cfg.robot["material"][
            "roughness"
        ]

        # Create output node
        n_output = node_list.new("ShaderNodeOutputMaterial")

        # Link shaders
        tl = l_mat.node_tree.links

        # Link texture image and normal map
        tl.new(n_uv_map.outputs[0], n_mix_col_map.inputs[1])
        tl.new(n_mix_col_map.outputs[0], n_principled.inputs[0])
        if normal_path is not None:
            tl.new(n_norm_map.outputs["Color"], n_norm_map_conv.inputs["Color"])
            tl.new(n_norm_map_conv.outputs["Normal"], n_principled.inputs["Normal"])
        tl.new(n_principled.outputs[0], n_output.inputs[0])

        return l_mat

    def set_tracking_target(self, target):
        # Ensure object is selected to receive added constraints
        bpy.context.view_layer.objects.active = self.obj

        if "Copy Rotation" not in self.obj.constraints:
            bpy.ops.object.constraint_add(type="COPY_ROTATION")

        rot_copy_constr = self.obj.constraints["Copy Rotation"]
        rot_copy_constr.name = "robot_copy_rot"
        rot_copy_constr.target = target

        rot_copy_constr.use_x = False
        rot_copy_constr.use_y = False
        rot_copy_constr.use_z = True

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
            var = scene_cfg.resources["robot"]["kinematics_variance"]
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
        self.obj.location = cfg["position"]
        # Randomly reassign robot colour
        col = randint(0, 1)
        for k in self.objs.keys():
            self.mat[k].node_tree.nodes["Mix"].inputs[2].default_value = (
                col,
                col,
                col,
                1,
            )

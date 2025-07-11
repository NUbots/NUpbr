#!/usr/local/blender -P

import os
import bpy
import copy
import numpy as np

from config import blend_config as blend_cfg

from scene.blender_object import BlenderObject


class Ball(BlenderObject):
    def __init__(self, name, class_index, ball_info):
        self.mat = None
        self.obj = None
        self.sc_plane = None
        self.pass_index = class_index
        self.name = name
        self.colour_path = None
        self.normal_path = None
        self.mesh_path = None
        self.roughness = 1.0

    # Setup ball object
    def construct(self, ball_info, radius, standard_deviation):
        ball_mesh = None
        ball = None

        # If there already exists a ball object bound to this class, destroy it
        if self.obj is not None:
            bpy.ops.object.select_all(action="DESELECT")
            self.obj.select_set(state=True)
            bpy.ops.object.delete()

        # Load mesh or create UV sphere
        if ball_info["mesh_path"] is not None:
            # Determine new object
            prev_obj_names = [x.name for x in bpy.data.objects]
            # Load fbx mesh
            # TODO: Support other mesh types
            ball_mesh = bpy.ops.import_scene.fbx(filepath=ball_info["mesh_path"])

            # Determine new ball name (by picking first result not in previous list)
            # (Should always only result in one new object)
            ball_name = [
                x.name for x in bpy.data.objects if x.name not in prev_obj_names
            ]
            ball = bpy.data.objects[ball_name[0]]
        else:
            # Add UV sphere for ball
            ball_mesh = bpy.ops.mesh.primitive_uv_sphere_add(
                segments=blend_cfg.ball["initial_cond"]["segments"],
                ring_count=blend_cfg.ball["initial_cond"]["ring_count"],
                calc_uvs=blend_cfg.ball["initial_cond"]["calc_uvs"],
            )
            ball = bpy.data.objects["Sphere"]

        # Make ball correct size
        # Randomise slightly for variance
        ball.dimensions = (radius * 2.0, radius * 2.0, radius * 2.0) + np.random.normal(
            0, standard_deviation, 3
        )

        # Make ball active object
        bpy.context.view_layer.objects.active = ball

        # Add UV sphere for ball
        ball.name = self.name
        ball.location = (0, 0, 0)
        ball.pass_index = self.pass_index

        # Add material to ball material slots
        self.mat = self.create_mat(
            blend_cfg.ball["material"], ball_info["colour_path"], ball_info["norm_path"]
        )
        ball.data.materials.append(self.mat)

        # Create subdiv surface modifiers if we have a new UV sphere
        if ball_info["mesh_path"] is None:
            bpy.ops.object.modifier_add(type="SUBSURF")
            ball.modifiers["Subdivision"].name = "Ball_Subsurf"
            ball_subsurf = ball.modifiers["Ball_Subsurf"]
            ball_subsurf.levels = blend_cfg.ball["subsurf_mod"]["levels"]
            ball_subsurf.render_levels = blend_cfg.ball["subsurf_mod"]["rend_levels"]

        self.obj = ball

    # Create material for the ball
    def create_mat(self, m_cfg, colour_path, normal_path):
        b_mat = bpy.data.materials.new("Ball_Mat")

        # Enable use of material nodes
        b_mat.use_nodes = True

        # Get our node list to construct our material
        node_list = b_mat.node_tree.nodes

        # Clear node tree of default settings
        for node in node_list:
            node_list.remove(node)

        # Construct node tree

        # Create colour texture image of ball UV map
        n_uv_map = node_list.new("ShaderNodeTexImage")
        n_uv_map.name = "UV_Image"

        try:
            img = bpy.data.images.load(colour_path)
        except:
            raise NameError("Cannot load image {0}".format(colour_path))
        n_uv_map.image = img

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

        # Create principled node
        n_principled = node_list.new("ShaderNodeBsdfPrincipled")
        n_principled.inputs[4].default_value = blend_cfg.ball["material"]["metallic"]
        n_principled.inputs[7].default_value = blend_cfg.ball["material"]["roughness"]
        self.roughness = blend_cfg.ball["material"]["roughness"]

        # Create output node
        n_output = node_list.new("ShaderNodeOutputMaterial")

        # Link shaders
        tl = b_mat.node_tree.links

        # Link texture image and normal map
        tl.new(n_uv_map.outputs[0], n_principled.inputs[0])
        if normal_path is not None:
            tl.new(n_norm_map.outputs[0], n_principled.inputs[16])
        tl.new(n_principled.outputs[0], n_output.inputs[0])

        return b_mat

    # Update ball UV map
    def update_texture(self, colour_path, norm_path=None):
        # If we have a colour map, update it
        b_mat = bpy.data.materials["Ball_Mat"]
        n_uv_map = b_mat.node_tree.nodes["UV_Image"]
        try:
            img = bpy.data.images.load(colour_path)
        except:
            raise NameError("Cannot load image {0}".format(colour_path))

        n_uv_map.image = img

        # If we have a normal map, update it
        if norm_path is not None:
            n_norm_map = b_mat.node_tree.nodes["Norm_Map"]
            try:
                norm_map = bpy.data.images.load(norm_path)
            except:
                raise NameError("Cannot load image {0}".format(norm_path))

            n_norm_map.image = norm_map

    def update(self, ball_data, ball_cfg):

        # Update the ball mesh/textures
        self.construct(ball_data, ball_cfg["radius"], ball_cfg["standard_deviation"])

        self.move(ball_cfg["position"])
        self.rotate(ball_cfg["rotation"])

#!/usr/local/blender -P

import os
import bpy

from config import scene_config as scene_cfg
from config import blend_config as blend_cfg

class Ball:
    def __init__(self, name, class_index, path):
        self.mat = None
        self.obj = None
        self.pass_index = class_index
        self.name = name
        self.construct(path)

    # Move relative to field origin
    def move(self, loc):
        self.obj.location = loc

    # Move relative to current position
    def offset(self, loc):
        self.obj.location = (
            self.obj.location[0] + loc[0],
            self.obj.location[1] + loc[1],
            self.obj.location[2] + loc[2],
        )

    def rotate(self, rot):
        self.rot = rot
        self.obj.rotation_euler = rot

    # Setup field object
    def construct(self, img_path):
        # Add plane for field
        ball_mesh = bpy.ops.mesh.primitive_uv_sphere_add(
            segments=blend_cfg.ball['initial_cond']['segments'],
            ring_count=blend_cfg.ball['initial_cond']['ring_count'],
            calc_uvs=blend_cfg.ball['initial_cond']['calc_uvs'],
        )
        # Add UV sphere for ball
        ball = bpy.data.objects['Sphere']
        ball.name = self.name
        ball.scale = (scene_cfg.ball['radius'], scene_cfg.ball['radius'], scene_cfg.ball['radius'])
        ball.location = (0., 0., 0.)
        ball.pass_index = self.pass_index

        # Add material to ball material slots
        self.mat = self.create_mat(blend_cfg.ball['material'], img_path)
        ball.data.materials.append(self.mat)

        # Create subdiv surface modifiers
        bpy.ops.object.modifier_add(type='SUBSURF')
        ball.modifiers['Subsurf'].name = 'Ball_Subsurf'
        ball_subsurf = ball.modifiers['Ball_Subsurf']
        ball_subsurf.levels = blend_cfg.ball['subsurf_mod']['levels']
        ball_subsurf.render_levels = blend_cfg.ball['subsurf_mod']['rend_levels']

        self.obj = ball

    # Create material for the field
    def create_mat(self, m_cfg, img_path):
        b_mat = bpy.data.materials.new('Ball_Mat')

        # Enable use of material nodes
        b_mat.use_nodes = True

        # Get our node list to construct our material
        node_list = b_mat.node_tree.nodes

        # Clear node tree of default settings
        for node in node_list:
            node_list.remove(node)

        # Construct node tree

        # Create texture image of field UV map
        n_uv_map = node_list.new('ShaderNodeTexImage')

        try:
            img = bpy.data.images.load(img_path)
        except:
            raise NameError('Cannot load image {0}'.format(img_path))
        n_uv_map.image = img

        # Create principled node
        n_principled = node_list.new('ShaderNodeBsdfPrincipled')
        n_principled.inputs[4].default_value = blend_cfg.ball['material']['metallic']
        n_principled.inputs[7].default_value = blend_cfg.ball['material']['roughness']

        # Create output node
        n_output = node_list.new('ShaderNodeOutputMaterial')

        # Link shaders
        tl = b_mat.node_tree.links

        # Link texture image
        tl.new(n_uv_map.outputs[0], n_principled.inputs[0])
        tl.new(n_principled.outputs[0], n_output.inputs[0])

        return b_mat

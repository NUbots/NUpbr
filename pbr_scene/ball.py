#!/usr/local/blender -P

import os
import bpy
import sys
import random as rand

# TODO: Remove hacky include
# Add our current position to path to include our config files
sys.path.insert(0, '.')
sys.path.insert(0, '../field_uv_generation/')

import environment as env
import scene_config as scene_cfg
import blend_config as blend_cfg

class Ball:
    def __init__(self):
        self.loc = (0., 0., 0.)
        self.mat = None
        self.obj = None

    # Create material for the field
    def create_ball_mat(self, b_object, m_cfg):
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
        uv_maps = os.listdir(scene_cfg.ball['uv_path'])
        # Ensure only .jpg or .png files are read
        uv_maps = [x for x in uv_maps if x[x.rfind('.'):] in scene_cfg.ball['uv_img_types']]

        img_path = os.path.join(scene_cfg.ball['uv_path'], uv_maps[rand.randint(0, len(uv_maps) - 1)])
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

    # Setup field object
    def construct_ball(self):
        # Add plane for field
        ball_mesh = bpy.ops.mesh.primitive_uv_sphere_add(
            segments=blend_cfg.ball['initial_cond']['segments'],
            ring_count=blend_cfg.ball['initial_cond']['ring_count'],
            calc_uvs=blend_cfg.ball['initial_cond']['calc_uvs'],
        )
        # Add UV sphere for ball
        ball = bpy.data.objects['Sphere']
        ball.name = 'Ball'
        ball.scale = (scene_cfg.ball['radius'], scene_cfg.ball['radius'], scene_cfg.ball['radius'])
        ball.location = (0., 0., 1.5 * scene_cfg.ball['radius'])

        # Add material to ball material slots
        self.mat = self.create_ball_mat(ball, blend_cfg.ball['material'])
        ball.data.materials.append(self.mat)

        # Create subdiv surface modifiers
        bpy.ops.object.modifier_add(type='SUBSURF')
        ball.modifiers['Subsurf'].name = 'Ball_Subsurf'
        ball_subsurf = ball.modifiers['Ball_Subsurf']
        ball_subsurf.levels = blend_cfg.ball['subsurf_mod']['levels']
        ball_subsurf.render_levels = blend_cfg.ball['subsurf_mod']['rend_levels']

        self.obj = ball

    def move_ball(self, loc):
        self.loc = loc
        self.obj.location = (
            self.obj.location[0] + loc[0],
            self.obj.location[1] + loc[1],
            self.obj.location[2] + loc[2],
        )

if __name__ == '__main__':
    # Clear default environment
    env.clear_env()
    # Setup render settings
    env.setup_render()
    # Setup HRDI environment
    env.setup_hdri_env()

    b = Ball()
    b.construct_ball()
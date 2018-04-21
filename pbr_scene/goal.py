#!C:\"Program Files"\"Blender Foundation"\Blender\blender -P

import os
import bpy
import sys
import random as rand
from math import pi

# TODO: Remove hacky include
# Add our current position to path to include our config files
sys.path.insert(0, '.')
sys.path.insert(0, '../field_uv_generation/')

import environment as env
import scene_config as scene_cfg
import blend_config as blend_cfg

class Goal:
    def __init__(self):
        self.loc = (0., 0., 0.)
        self.mat = None
        self.obj = None

    # Create material for the field
    def create_goal_mat(self, g_object, m_cfg):
        g_mat = None
        return g_mat

    # Create corner curve to apply to goal post
    def create_corner_curve(self, c_cfg):
        # Define corner radius to avoid extra multiplications
        corner_radius = scene_cfg.goal['post_width'] / 2.

        # Create corner Bezier curve
        corner_curve = bpy.ops.curve.primitive_bezier_curve_add()

        curve = bpy.data.objects['BezierCurve']
        curve.name = 'Goal_Corner_Curve'
        # curve.location = (0, 0, scene_cfg.goal['height'])

        print(dir(curve.data.splines.active.bezier_points[0]))
        print(len(curve.data.splines.active.bezier_points))

        [p0, p1] = [
            curve.data.splines.active.bezier_points[0],
            curve.data.splines.active.bezier_points[1],
        ]
        # Set first point
        p0.co = (0., 0., scene_cfg.goal['height'])
        p0.handle_left = (0., 0., scene_cfg.goal['height'] - corner_radius)
        p0.handle_right = (0., 0., scene_cfg.goal['height'] + corner_radius)

        # Set second point
        p1.co = (0., corner_radius, scene_cfg.goal['height'] + corner_radius)
        p1.handle_left = (0., 0., scene_cfg.goal['height'] + corner_radius)
        p1.handle_right = (0., scene_cfg.goal['post_width'], scene_cfg.goal['height'] + corner_radius)

        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY')

        return curve

    def create_corner(self, c_cfg):
        # Create the corner of the goals to be rounded
        corner_mesh = bpy.ops.mesh.primitive_circle_add(
            radius=scene_cfg.goal['post_width'] / 2.,
            vertices=blend_cfg.goal['initial_cond']['vertices'],
            calc_uvs=blend_cfg.ball['initial_cond']['calc_uvs'],
        )
        corner = bpy.data.objects['Circle']
        corner.name = 'Goal_Corner'
        corner.location = (0, 0, scene_cfg.goal['height'])

        # Create extrusion of the goal corner, slicing into n slices
        #  where n is specified in blend_config.goal['corner']['divisions']
        partial_extrude_amt = scene_cfg.goal['post_width'] / blend_cfg.goal['corner']['divisions']

        # Switch modes and be ready to extrude
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type='VERT')
        bpy.ops.mesh.select_all(action='SELECT')

        # Extrude n times
        for i in range(0, int(blend_cfg.goal['corner']['divisions'])):
            bpy.ops.mesh.extrude_region_move(
                MESH_OT_extrude_region={"mirror": False},
                TRANSFORM_OT_translate={"value": (0, 0, partial_extrude_amt)},
            )

        bpy.ops.object.mode_set(mode='OBJECT')

        return corner

    # Setup field object
    def construct_goal(self):
        # Add plane for field
        goal_post_mesh = bpy.ops.mesh.primitive_circle_add(
            radius=scene_cfg.goal['post_width'] / 2.,
            vertices=blend_cfg.goal['initial_cond']['vertices'],
            calc_uvs=blend_cfg.ball['initial_cond']['calc_uvs'],
        )
        # Change name of goal post
        goal_post = bpy.data.objects['Circle']
        goal_post.name = 'Goal_Post'
        goal_post.location = (0, 0, 0)

        # Extrude the goal post to proper length
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type='VERT')
        bpy.ops.mesh.select_all(action='SELECT')

        bpy.ops.mesh.extrude_region_move(
            MESH_OT_extrude_region={"mirror": False},
            TRANSFORM_OT_translate={"value": (0, 0, scene_cfg.goal['height'])},
        )

        bpy.ops.object.mode_set(mode='OBJECT')

        # Get goal corner
        corner = self.create_corner(blend_cfg.goal['corner'])
        # Get corner curve
        curve = self.create_corner_curve(blend_cfg.goal['corner']['curve'])

        self.obj = goal_post

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

    g = Goal()
    g.construct_goal()

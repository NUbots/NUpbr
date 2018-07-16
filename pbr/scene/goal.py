#!/usr/local/blender -P

import os
import bpy
import random as rand
from math import pi

from config import scene_config as scene_cfg
from config import blend_config as blend_cfg

from scene.blender_object import BlenderObject


class Goal(BlenderObject):
    def __init__(self, class_index):
        self.loc = (0., 0., 0.)
        self.mat = None
        self.obj = None
        self.pass_index = class_index
        self.construct()

    # Setup field object
    def construct(self):
        # Define corner radius to avoid extra multiplications
        corner_radius = scene_cfg.goal['post_width'] / 2.

        goal_post = self.create_post(
            name='Goal_Post',
            extrude=(0., 0., scene_cfg.goal['height']),
        )

        # Get corner curve
        curve = self.create_corner_curve(blend_cfg.goal['corner_curve'])
        # Convert curve to mesh
        bpy.ops.object.convert(target='MESH', keep_original=False)

        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY')

        # Create our goal rear to join after we have created the front of the goals
        goal_rear = self.create_goal_rear(curve)

        self.join_objs([goal_post, curve])

        # Create second goal post
        goal_post_copy = self.copy_obj(
            goal_post,
            name='Goal_Post_copy',
            loc=(0., scene_cfg.goal['width'], 0.),
            rot=(0., 0., pi),
        )

        # Create crossbar
        crossbar = self.create_post(
            name='Crossbar',
            loc=(0., corner_radius, scene_cfg.goal['height'] + corner_radius),
            rot=(pi / 2., 0., 0.),
            extrude=(0., scene_cfg.goal['width'] - 2 * corner_radius, 0.),
        )

        # Create goals with posts and crossbar
        self.join_objs([goal_post, goal_post_copy, crossbar])
        # Create goals with front and back
        self.join_objs([goal_post, goal_rear])

        # Redefine name to be goal instead of goal post for clarity
        goal = goal_post
        goal.name = 'Goal'
        goal.location = (
            goal.location[0] + 0.,
            goal.location[1] - scene_cfg.goal['width'] / 2.,
            goal.location[2] + 0.,
        )
        goal.pass_index = self.pass_index

        # Reset origin to centre of geometry
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY')

        # Apply goal material
        self.mat = self.create_mat(goal, blend_cfg.goal['material'])
        goal.data.materials.append(self.mat)

        self.obj = goal_post

    # Utility function for joining objects together
    def join_objs(self, objs):
        # Create copy of context
        context = bpy.context.copy()
        # Select our active and selected objects
        context['active_object'] = objs[0]
        context['selected_objects'] = objs
        # Select all of our available editable bases
        context['selected_editable_bases'] = [
            bpy.context.scene.object_bases[obj.name] for obj in objs
        ]
        # Join objects
        bpy.ops.object.join(context)
        bpy.data.objects[objs[0].name].select = True

    # Utility function for copying objects
    def copy_obj(self, obj, name, loc, rot):
        obj_copy = obj.copy()
        obj_copy.data = obj.data.copy()
        obj_copy.name = name
        obj_copy.location = loc
        obj_copy.rotation_euler = rot
        obj_copy.animation_data_clear()
        bpy.context.scene.objects.link(obj_copy)

        bpy.data.objects[obj.name].select = False
        bpy.data.objects[obj_copy.name].select = False

        return obj_copy

    # Create material for the field
    def create_mat(self, g_object, m_cfg):
        g_mat = bpy.data.materials.new('Goal_Mat')

        # Enable use of material nodes
        g_mat.use_nodes = True

        # Get our node list to construct our material
        node_list = g_mat.node_tree.nodes

        # Clear node tree of default settings
        for node in node_list:
            node_list.remove(node)

        # Construct node tree
        # Create principled node
        n_principled = node_list.new('ShaderNodeBsdfPrincipled')
        n_principled.inputs[0].default_value = blend_cfg.goal['material'][
            'colour']
        n_principled.inputs[4].default_value = blend_cfg.goal['material'][
            'metallic']
        n_principled.inputs[7].default_value = blend_cfg.goal['material'][
            'roughness']

        # Create output node
        n_output = node_list.new('ShaderNodeOutputMaterial')

        # Link shaders
        tl = g_mat.node_tree.links

        # Link texture image
        tl.new(n_principled.outputs[0], n_output.inputs[0])

        return g_mat

    # Create corner curve to apply to goal post
    def create_corner_curve(self, c_cfg):
        # Define corner radius to avoid extra multiplications
        corner_radius = scene_cfg.goal['post_width'] / 2.

        # Create corner Bezier curve
        corner_curve = bpy.ops.curve.primitive_bezier_curve_add()

        curve = bpy.data.objects['BezierCurve']

        # Set curve properties
        curve.name = 'Goal_Corner_Curve'
        curve.data.fill_mode = blend_cfg.goal['corner_curve']['fill']
        curve.data.bevel_depth = corner_radius
        curve.data.bevel_resolution = int(
            blend_cfg.goal['initial_cond']['vertices'] / 2.)

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
        p1.handle_right = (0., scene_cfg.goal['post_width'],
                           scene_cfg.goal['height'] + corner_radius)

        # Move origin to centre of geometry
        # bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY')

        return curve

    # Create goal post
    def create_post(self,
                    name,
                    loc=(0., 0., 0.),
                    rot=(0., 0., 0.),
                    extrude=(0., 0., 0.)):
        # Define corner radius to avoid extra multiplications
        corner_radius = scene_cfg.goal['post_width'] / 2.

        # Add plane for field
        mesh = bpy.ops.mesh.primitive_circle_add(
            radius=corner_radius,
            vertices=blend_cfg.goal['initial_cond']['vertices'],
            calc_uvs=blend_cfg.ball['initial_cond']['calc_uvs'],
            rotation=rot,
        )
        # Change name of goal post
        goal_post = bpy.data.objects['Circle']
        goal_post.name = name
        goal_post.location = loc

        # Extrude the goal post to proper length
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type='VERT')
        bpy.ops.mesh.select_all(action='SELECT')

        bpy.ops.mesh.extrude_region_move(
            MESH_OT_extrude_region={"mirror": False},
            TRANSFORM_OT_translate={"value": extrude},
        )

        bpy.ops.object.mode_set(mode='OBJECT')

        return goal_post

    def create_goal_rear(self, curve):
        # Define corner radius to avoid extra multiplications
        corner_radius = scene_cfg.goal['post_width'] / 2.
        # Left bottom
        lb_curve = self.copy_obj(
            curve,
            name='LT_Curve',
            loc=(scene_cfg.goal['depth'], corner_radius / 4., corner_radius),
            rot=(0., pi / 2., 0.),
        )
        lb_post = self.create_post(
            name='LB_Post',
            loc=(0., 0., corner_radius),
            rot=(0., -pi / 2., 0.),
            extrude=(scene_cfg.goal['depth'] - corner_radius / 2., 0., 0.),
        )
        # Left top
        lt_curve = self.copy_obj(
            curve,
            name='LB_Curve',
            loc=(scene_cfg.goal['depth'], corner_radius / 4.,
                 scene_cfg.goal['net_height']),
            rot=(0., pi / 2., 0.),
        )
        lt_post = self.create_post(
            name='LT_Post',
            loc=(0., 0., scene_cfg.goal['net_height']),
            rot=(0., -pi / 2., 0.),
            extrude=(scene_cfg.goal['depth'] - corner_radius / 2., 0., 0.),
        )

        # Right bottom
        rb_curve = self.copy_obj(
            curve,
            name='RB_Curve',
            loc=(scene_cfg.goal['depth'],
                 scene_cfg.goal['width'] - corner_radius / 4., corner_radius),
            rot=(0., pi / 2., pi / 2.),
        )
        rb_post = self.create_post(
            name='RB_Post',
            loc=(0., scene_cfg.goal['width'], corner_radius),
            rot=(0., -pi / 2., 0.),
            extrude=(scene_cfg.goal['depth'] - corner_radius / 2., 0., 0.),
        )
        # Right top
        rt_curve = self.copy_obj(
            curve,
            name='RT_Curve',
            loc=(scene_cfg.goal['depth'],
                 scene_cfg.goal['width'] - corner_radius / 4.,
                 scene_cfg.goal['net_height']),
            rot=(0., pi / 2., pi / 2.),
        )
        rt_post = self.create_post(
            name='RT_Post',
            loc=(0., scene_cfg.goal['width'], scene_cfg.goal['net_height']),
            rot=(0., -pi / 2., 0.),
            extrude=(scene_cfg.goal['depth'] - corner_radius / 2., 0., 0.),
        )

        # Back bottom
        bb_post = self.create_post(
            name='BB_Post',
            loc=(scene_cfg.goal['depth'] + corner_radius / 4.,
                 corner_radius / 2., scene_cfg.goal['net_height']),
            rot=(pi / 2., 0., 0.),
            extrude=(0., scene_cfg.goal['width'] - corner_radius, 0.),
        )
        bt_post = self.create_post(
            name='BT_Post',
            loc=(scene_cfg.goal['depth'] + corner_radius / 4.,
                 corner_radius / 2., corner_radius),
            rot=(pi / 2., 0., 0.),
            extrude=(0., scene_cfg.goal['width'] - corner_radius, 0.),
        )

        # Back verticals
        lv_post = self.create_post(
            name='BB_Post',
            loc=(scene_cfg.goal['depth'], corner_radius / 4., corner_radius),
            extrude=(0., 0., scene_cfg.goal['net_height'] - corner_radius),
        )
        rv_post = self.create_post(
            name='BB_Post',
            loc=(scene_cfg.goal['depth'],
                 scene_cfg.goal['width'] - corner_radius / 4., corner_radius),
            extrude=(0., 0., scene_cfg.goal['net_height'] - corner_radius),
        )

        # Make single goal back object
        self.join_objs([
            lb_curve,
            lb_post,
            lt_curve,
            lt_post,
            rb_curve,
            rb_post,
            rt_curve,
            rt_post,
            bb_post,
            bt_post,
            lv_post,
            rv_post,
        ])

        # Rename the object for clarity
        goal_back = lb_curve
        goal_back.name = 'Goal_Back'

        return goal_back

    def get_num_objs(self):
        print(len(bpy.data.objects))
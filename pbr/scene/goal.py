#!/usr/local/blender -P

import os
import bpy
import random as rand
from math import pi

from config import blend_config as blend_cfg

from scene.blender_object import BlenderObject

class Goal(BlenderObject):
    def __init__(self, class_index):
        self.mat = None
        self.obj = None
        self.rear = None
        self.pass_index = class_index

    # Setup field object
    def update(self, goal_config):

        # Delete object if it already exists
        if self.obj is not None:
            bpy.data.objects.remove(self.obj)
        if self.rear is not None:
            bpy.data.objects.remove(self.rear)

        # Define corner radius to avoid extra multiplications
        corner_radius = goal_config['post_width'] / 2

        goal_post = self.create_post(
            goal_config,
            name='Goal_Post',
            extrude=(0, 0, goal_config['height']),
        )

        # Get corner curve
        curve = self.create_corner_curve(goal_config, blend_cfg.goal['corner_curve'])
        # Convert curve to mesh
        bpy.ops.object.convert(target='MESH', keep_original=False)

        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY')

        # Create our goal rear to join after we have created the front of the goals
        goal_rear = self.create_goal_rear(goal_config, curve)

        self.join_objs([goal_post, curve])

        # Create second goal post
        goal_post_copy = self.copy_obj(
            goal_post,
            name='Goal_Post_copy',
            loc=(0, goal_config['width'], 0),
            rot=(0, 0, pi),
        )

        # Create crossbar
        crossbar_y_loc = corner_radius if goal_config['shape'] == 'circular' else -corner_radius
        crossbar_ext_offset = -(2 * corner_radius) if goal_config['shape'] == 'circular' else 2 * corner_radius
        crossbar = self.create_post(
            goal_config,
            name='Crossbar',
            loc=(0, crossbar_y_loc, goal_config['height'] + corner_radius),
            rot=(pi / 2, 0, 0),
            extrude=(0, goal_config['width'] + crossbar_ext_offset, 0),
        )

        # Create goals with posts and crossbar
        self.join_objs([goal_post, goal_post_copy, crossbar])

        # Connect back of goals to front
        goal_rear.parent = goal_post

        # Redefine name to be goal instead of goal post for clarity
        goal = goal_post
        goal.name = 'Goal'
        goal.location = (
            goal.location[0] + 0,
            goal.location[1] - goal_config['width'] / 2,
            goal.location[2] + 0,
        )
        goal.pass_index = self.pass_index

        # Reset origin to centre of geometry
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY')

        # Apply goal material
        self.mat = self.create_mat(goal, blend_cfg.goal['material'])
        goal.data.materials.append(self.mat)

        # Apply goal material
        self.mat = self.create_mat(goal_rear, blend_cfg.goal['material'])
        goal_rear.data.materials.append(self.mat)

        self.obj = goal_post
        self.rear = goal_rear

    def hide_object(self, to_hide):
        self.obj.hide_render = to_hide
        self.rear.hide_render = to_hide

    # Utility function for joining objects together
    def join_objs(self, objs):
        # Create copy of context
        context = bpy.context.copy()
        # Select our active and selected objects
        context['active_object'] = objs[0]
        context['selected_objects'] = objs
        # Select all of our available editable bases
        context['selected_editable_bases'] = [bpy.context.scene.object_bases[obj.name] for obj in objs]
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
        n_principled.inputs[0].default_value = blend_cfg.goal['material']['colour']
        n_principled.inputs[4].default_value = blend_cfg.goal['material']['metallic']
        n_principled.inputs[7].default_value = blend_cfg.goal['material']['roughness']

        # Create output node
        n_output = node_list.new('ShaderNodeOutputMaterial')

        # Link shaders
        tl = g_mat.node_tree.links

        # Link texture image
        tl.new(n_principled.outputs[0], n_output.inputs[0])

        return g_mat

    # Create corner curve to apply to goal post
    def create_corner_curve(self, goal_config, c_cfg):
        # Define corner radius to avoid extra multiplications
        corner_radius = goal_config['post_width'] / 2

        if goal_config['shape'] == 'circular':
            # Create corner Bezier curve
            corner_curve = bpy.ops.curve.primitive_bezier_curve_add()

            curve = bpy.data.objects['BezierCurve']

            # Set curve properties
            curve.name = 'Goal_Corner_Curve'
            curve.data.fill_mode = blend_cfg.goal['corner_curve']['fill']
            curve.data.bevel_depth = corner_radius
            curve.data.bevel_resolution = int(blend_cfg.goal['initial_cond']['vertices'] / 2)

            [p0, p1] = [
                curve.data.splines.active.bezier_points[0],
                curve.data.splines.active.bezier_points[1],
            ]
            # Set first point
            p0.co = (0, 0, goal_config['height'])
            p0.handle_left = (0, 0, goal_config['height'] - corner_radius)
            p0.handle_right = (0, 0, goal_config['height'] + corner_radius)

            # Set second point
            p1.co = (0, corner_radius, goal_config['height'] + corner_radius)
            p1.handle_left = (0, 0, goal_config['height'] + corner_radius)
            p1.handle_right = (0, goal_config['post_width'], goal_config['height'] + corner_radius)
        elif goal_config['shape'] == 'square':
            curve = self.create_post(
                goal_config=goal_config,
                name='Goal_Corner_Curve',
                loc=(0, 0, goal_config['height'] - corner_radius),
                extrude=(0, 0, 2 * corner_radius),
            )

        # Move origin to centre of geometry
        # bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY')

        return curve

    # Create goal post
    def create_post(self, goal_config, name, loc=(0, 0, 0), rot=(0, 0, 0), extrude=(0, 0, 0)):
        # Define corner radius to avoid extra multiplications
        corner_radius = goal_config['post_width'] / 2

        # Add plane for field
        if goal_config['shape'] == 'circular':
            mesh = bpy.ops.mesh.primitive_circle_add(
                radius=corner_radius,
                vertices=blend_cfg.goal['initial_cond']['vertices'],
                calc_uvs=blend_cfg.ball['initial_cond']['calc_uvs'],
                rotation=rot,
            )
            # Change name of goal post
            goal_post = bpy.data.objects['Circle']
        elif goal_config['shape'] == 'square':
            mesh = bpy.ops.mesh.primitive_plane_add(
                radius=corner_radius,
                calc_uvs=blend_cfg.ball['initial_cond']['calc_uvs'],
                rotation=rot,
            )
            # Change name of goal post
            goal_post = bpy.data.objects['Plane']

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

    def create_goal_rear(self, goal_config, curve):
        # Define corner radius to avoid extra multiplications
        corner_radius = goal_config['post_width'] / 2
        # Left bottom
        lb_curve = self.copy_obj(
            curve,
            name='LT_Curve',
            loc=(goal_config['depth'], corner_radius / 4, corner_radius),
            rot=(0, pi / 2, 0),
        )
        lb_post = self.create_post(
            goal_config,
            name='LB_Post',
            loc=(0, 0, corner_radius),
            rot=(0, -pi / 2, 0),
            extrude=(goal_config['depth'] - corner_radius / 2, 0, 0),
        )
        # Left top
        lt_curve = self.copy_obj(
            curve,
            name='LB_Curve',
            loc=(goal_config['depth'], corner_radius / 4, goal_config['net_height']),
            rot=(0, pi / 2, 0),
        )
        lt_post = self.create_post(
            goal_config,
            name='LT_Post',
            loc=(0, 0, goal_config['net_height']),
            rot=(0, -pi / 2, 0),
            extrude=(goal_config['depth'] - corner_radius / 2, 0, 0),
        )

        # Right bottom
        rb_curve = self.copy_obj(
            curve,
            name='RB_Curve',
            loc=(goal_config['depth'], goal_config['width'] - corner_radius / 4, corner_radius),
            rot=(0, pi / 2, pi / 2),
        )
        rb_post = self.create_post(
            goal_config,
            name='RB_Post',
            loc=(0, goal_config['width'], corner_radius),
            rot=(0, -pi / 2, 0),
            extrude=(goal_config['depth'] - corner_radius / 2, 0, 0),
        )
        # Right top
        rt_curve = self.copy_obj(
            curve,
            name='RT_Curve',
            loc=(goal_config['depth'], goal_config['width'] - corner_radius / 4, goal_config['net_height']),
            rot=(0, pi / 2, pi / 2),
        )
        rt_post = self.create_post(
            goal_config,
            name='RT_Post',
            loc=(0, goal_config['width'], goal_config['net_height']),
            rot=(0, -pi / 2, 0),
            extrude=(goal_config['depth'] - corner_radius / 2, 0, 0),
        )

        # Back bottom
        bb_post = self.create_post(
            goal_config,
            name='BB_Post',
            loc=(goal_config['depth'] + corner_radius / 4, corner_radius / 2, goal_config['net_height']),
            rot=(pi / 2, 0, 0),
            extrude=(0, goal_config['width'] - corner_radius, 0),
        )
        bt_post = self.create_post(
            goal_config,
            name='BT_Post',
            loc=(goal_config['depth'] + corner_radius / 4, corner_radius / 2, corner_radius),
            rot=(pi / 2, 0, 0),
            extrude=(0, goal_config['width'] - corner_radius, 0),
        )

        # Back verticals
        lv_post = self.create_post(
            goal_config,
            name='BB_Post',
            loc=(goal_config['depth'], corner_radius / 4, corner_radius),
            extrude=(0, 0, goal_config['net_height'] - corner_radius),
        )
        rv_post = self.create_post(
            goal_config,
            name='BB_Post',
            loc=(goal_config['depth'], goal_config['width'] - corner_radius / 4, corner_radius),
            extrude=(0, 0, goal_config['net_height'] - corner_radius),
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

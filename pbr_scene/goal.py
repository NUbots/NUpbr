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
        curve.data.bevel_resolution = int(blend_cfg.goal['initial_cond']['vertices'] / 2.)

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

        # Move origin to centre of geometry
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY')

        return curve

    # Create goal post
    def create_post(self, name, loc=(0., 0., 0.), rot=(0., 0., 0.), extrude=(0., 0., 0.)):
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

    # Setup field object
    def construct_goal(self):
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

        self.join_objs([goal_post, curve])

        # Select our goal post for duplication
        bpy.data.objects[goal_post.name].select = True
        # Duplicate the object
        bpy.ops.object.duplicate(linked=0, mode='TRANSLATION')

        # Create second goal post
        goal_post_copy = bpy.data.objects[goal_post.name + '.001']
        goal_post_copy.name = 'Goal_Post_copy'
        goal_post_copy.location = (0., scene_cfg.goal['width'], 0.)
        goal_post_copy.rotation_euler = (0., 0., pi)

        # Create crossbar
        crossbar = self.create_post(
            name='Crossbar',
            loc=(0., corner_radius, scene_cfg.goal['height'] + corner_radius),
            rot=(pi / 2., 0., 0.),
            extrude=(0., scene_cfg.goal['width'] - 2 * corner_radius, 0.),
        )

        # Create goals with posts and crossbar
        self.join_objs([goal_post, goal_post_copy, crossbar])

        # Redefine name to be goal instead of goal post for clarity
        goal = goal_post
        goal.name = 'Goal'
        goal.location = (
            goal.location[0] + 0.,
            goal.location[1] - scene_cfg.goal['width'] / 2.,
            goal.location[2] + 0.,
        )

        # Reset origin to centre of geometry
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY')

        # Apply goal material
        self.mat = self.create_goal_mat(goal, blend_cfg.goal['material'])
        goal.data.materials.append(self.mat)

        self.obj = goal_post

    def move_goal(self, loc):
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

    g1 = Goal()
    g1.construct_goal()
    g1.move_goal((scene_cfg.field['length'] / 2., 0., 0.))

    g2 = Goal()
    g2.construct_goal()
    g2.move_goal((-scene_cfg.field['length'] / 2., 0., 0.))

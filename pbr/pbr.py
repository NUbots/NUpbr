#!/usr/local/blender -P

import os
import sys
import random as rand
import bpy
import re

# Add our current position to path to include package
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

from math import pi, sqrt, ceil

from config import scene_config as scene_cfg
from config import output_config as out_cfg

from scene import environment as env
from scene.ball import Ball
from scene.field import Field
from scene.goal import Goal
from scene.camera import Camera
from scene.camera_anchor import CameraAnchor

# from field_uv import generate_uv

DEG_TO_RAD = pi / 180.


# Import ball UV maps and meshes from ball import directory
def populate_balls(path):
    # Populate list of ball images and meshes
    files = os.listdir(path)

    # Create container for ball entries
    # Where each ball entry is a dictionary containing:
    #   colour image path,
    #   normal image path (optional),
    #   mesh file (optional)
    balls = []

    # Get sorted list of ball UV maps
    uv_maps = sorted([
        x for x in files
        if not os.path.isdir(os.path.join(path, x)) and x.rfind('.') != -1
        and x[x.rfind('.'):] in scene_cfg.ball['uv_img_types']
    ])

    type_count = 0
    image_suffix = ''
    for img_type in scene_cfg.ball['uv_img_types']:
        image_suffix += img_type
        if type_count + 1 < len(scene_cfg.ball['uv_img_types']):
            image_suffix += '|'
        type_count += 1

    norm_files = []
    mesh_files = []
    colour_files = []

    norm_regex = r'(.*)norm(a?l?)(.*)'
    col_regex = r'(.*)col(u?)or(s?)(.*)'
    mesh_regex = r'(.*)fbx'

    colour_path = None
    normal_path = None
    mesh_path = None

    for file in files:
        normal = re.search(norm_regex, file, re.I)
        colour = re.search(col_regex, file, re.I)
        mesh = re.search(mesh_regex, file, re.I)

        if colour is not None:
            colour_path = os.path.join(path, colour.group())
        if normal is not None:
            normal_path = os.path.join(path, normal.group())
        if mesh is not None:
            mesh_path = os.path.join(path, mesh.group())

    if colour_path is not None:
        balls.append({
            'colour_path': colour_path,
            'norm_path': normal_path,
            'mesh_path': mesh_path,
        })

    # Ensure only .jpg or .png files are read
    # TODO: Move check to ball class where ball will be constructed depending on import type
    ball_subdirs = sorted(
        [x for x in files if os.path.isdir(os.path.join(path, x))])

    for subdir in ball_subdirs:
        balls += populate_balls(os.path.join(path, subdir))

    return balls


def main():
    # Make UV map
    # generate_uv.main()

    ##############################################
    ##              ASSET LOADING               ##
    ##############################################

    # Populate list of hdr scenes
    scene_hdrs = os.listdir(scene_cfg.scene_hdr['path'])

    # Make sure we're only loading .hdr files
    scene_hdrs = [x for x in scene_hdrs if x[x.rfind('.'):] == '.hdr']
    hdr_index = 0
    hdr_path = os.path.join(scene_cfg.scene_hdr['path'], scene_hdrs[hdr_index])
    mask_path = hdr_path  # TODO

    # Create container for ball entries
    balls = populate_balls(scene_cfg.ball['ball_dir'])

    ball_index = 0
    curr_ball_info = balls[ball_index]

    ##############################################
    ##             ENVIRONMENT SETUP            ##
    ##############################################

    # Clear default environment
    env.clear_env()
    # Setup render settings
    env.setup_render()
    # Setup HRDI environment
    world = env.setup_hdri_env(hdr_path)

    # Setup render layers (visual, segmentation and field lines)
    render_layer_toggle = env.setup_segmentation_render_layers(
        len(scene_cfg.classes))

    ##############################################
    ##            SCENE CONSTRUCTION            ##
    ##############################################

    # Construct our default UV sphere ball
    ball = Ball(
        'Ball',
        scene_cfg.classes['ball']['index'],
        curr_ball_info['colour_path'],
        curr_ball_info['norm_path'],
        curr_ball_info['mesh_path'],
    )
    ball.move((0., 0., scene_cfg.ball['radius']))

    # Construct our goals
    goals = [
        Goal(scene_cfg.classes['goal']['index']),
        Goal(scene_cfg.classes['goal']['index'])
    ]
    goals[0].offset((scene_cfg.field['length'] / 2., 0., 0.))

    goals[1].offset(
        (-scene_cfg.field['length'] / 2. - 1.5 * scene_cfg.goal['depth'] +
         scene_cfg.goal['post_width'], 0., 0.))
    goals[1].rotate((0., 0., pi))

    # Construct our grass field
    field = Field(scene_cfg.classes['field']['index'])

    # Construct cameras
    cam_separation = 0 if out_cfg.output_stereo == False else scene_cfg.camera[
        'stereo_cam_dist']
    height = rand.uniform(scene_cfg.camera['limits']['position']['z'][0],
                          scene_cfg.camera['limits']['position']['z'][1])

    cam_l = Camera('Camera_L')
    cam_r = Camera('Camera_R')

    cam_l.move((-cam_separation / 2., 0., height))

    cam_l.set_tracking_target(ball.obj)
    # Set left camera to be parent camera
    # (and so all right camera movements are relative to the left camera position)
    cam_r.set_stereo_pair(cam_l.obj)

    cam_r.move((cam_separation, 0., 0.))

    # Create camera anchor target for random field images
    a = CameraAnchor()

    ##############################################
    ##               SCENE UPDATE               ##
    ##############################################

    cam_limits = scene_cfg.camera['limits']
    ball_limits = scene_cfg.ball['limits']

    # Batch size for each HDRI environment map
    env_batch_size = ceil(out_cfg.num_images / len(scene_hdrs))

    # Batch size for each ball in each HDRI environment map
    ball_batch_size = ceil(env_batch_size / len(balls))

    for frame_num in range(0, out_cfg.num_images):
        # Each ball gets even number of frames for each environment
        if frame_num > 0 and frame_num % ball_batch_size == 0:
            ball_index += 1
            curr_ball_info = balls[ball_index]
            # If we're using same UV sphere and only changing textures,
            #   recreating the UV sphere is unnecessary
            if curr_ball_info['mesh_path'] is None and ball.mesh_path is None:
                ball.update_texture(
                    curr_ball_info['colour_path'],
                    curr_ball_info['norm_path'],
                )
            # If we're changing meshes, completely reconstruct our ball
            else:
                ball.construct(
                    curr_ball_info['colour_path'],
                    curr_ball_info['norm_path'],
                    curr_ball_info['mesh_path'],
                )
            cam_l.set_tracking_target(ball.obj)

        # Each environment map gets even distribution of frames
        if frame_num % env_batch_size == 0:
            ball_index = 0
            if hdr_index + 1 < len(scene_hdrs):
                hdr_index += 1
            hdr_path = os.path.join(scene_cfg.scene_hdr['path'],
                                    scene_hdrs[hdr_index])
            cam_l.set_tracking_target(ball.obj)

        ## Update ball
        # Move ball
        ball.move((
            rand.uniform(ball_limits['position']['x'][0],
                         ball_limits['position']['x'][1]),
            rand.uniform(ball_limits['position']['y'][0],
                         ball_limits['position']['y'][1]),
            rand.uniform(ball_limits['position']['z'][0],
                         ball_limits['position']['z'][1]),
        ))
        # Rotate ball
        ball.rotate((
            rand.uniform(ball_limits['rotation']['pitch'][0],
                         ball_limits['rotation']['pitch'][1]) * DEG_TO_RAD,
            rand.uniform(ball_limits['rotation']['yaw'][0],
                         ball_limits['rotation']['yaw'][1]) * DEG_TO_RAD,
            rand.uniform(ball_limits['rotation']['roll'][0],
                         ball_limits['rotation']['roll'][1]) * DEG_TO_RAD,
        ))

        ## Update camera
        # Move camera
        cam_l.move((
            rand.uniform(cam_limits['position']['x'][0],
                         cam_limits['position']['x'][1]),
            rand.uniform(cam_limits['position']['y'][0],
                         cam_limits['position']['y'][1]),
            rand.uniform(cam_limits['position']['z'][0],
                         cam_limits['position']['z'][1]),
        ))

        cam_l.rotate((
            rand.uniform(cam_limits['rotation']['pitch'][0],
                         cam_limits['rotation']['pitch'][1]),
            rand.uniform(cam_limits['rotation']['yaw'][0],
                         cam_limits['rotation']['yaw'][1]),
            rand.uniform(cam_limits['rotation']['roll'][0],
                         cam_limits['rotation']['roll'][1]),
        ))

        # Move potential camera target
        a.move((
            rand.uniform(cam_limits['position']['x'][0],
                         cam_limits['position']['x'][1]),
            rand.uniform(cam_limits['position']['y'][0],
                         cam_limits['position']['y'][1]),
            rand.uniform(cam_limits['position']['z'][0],
                         cam_limits['position']['z'][1]),
        ))

        # Focus to goal if within second third of images
        if int(frame_num % env_batch_size) == int(env_batch_size / 3.):
            goal_index = rand.randint(0, 1)
            cam_l.set_tracking_target(goals[goal_index].obj)
        # Focus on random field if within third third of images
        elif int(frame_num % env_batch_size) == int((2 * env_batch_size) / 3.):
            cam_l.set_tracking_target(a.obj)

        ##############################################
        ##                RENDERING                 ##
        ##############################################

        filename = '{0:010}'.format(frame_num)

        # Establish camera list for either stereo or mono output
        cam_list = None
        if not out_cfg.output_stereo:
            cam_list = [{'obj': cam_l.obj, 'str': ''}]
        else:
            cam_list = [{
                'obj': cam_l.obj,
                'str': '_L'
            }, {
                'obj': cam_r.obj,
                'str': '_R'
            }]

        ## Render for each camera
        for cam in cam_list:
            bpy.context.scene.camera = cam['obj']
            render_layers = bpy.context.scene.render.layers

            ## Raw image rendering
            # Turn off all render layers
            for l in render_layers:
                l.use = False

            # Render raw image
            render_layers['RenderLayer'].use = True
            render_layer_toggle.check = False
            env.update_hdri_env(world, hdr_path)
            bpy.data.scenes['Scene'].render.filepath = os.path.join(
                out_cfg.image_dir, filename + cam['str'])
            bpy.ops.render.render(write_still=True)

            ## Mask image rendering
            # Turn on all render layers
            for l in render_layers:
                l.use = True

            # Render mask image
            render_layers['RenderLayer'].use = False
            render_layer_toggle.check = True
            env.update_hdri_env(world, mask_path)
            bpy.data.scenes['Scene'].render.filepath = os.path.join(
                out_cfg.mask_dir, filename + cam['str'])
            bpy.ops.render.render(write_still=True)


if __name__ == '__main__':
    main()
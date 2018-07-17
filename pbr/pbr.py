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

from field_uv import generate_uv

DEG_TO_RAD = pi / 180.

# Import assets from path as defined by asset_list
# Where asset list is a list of two-tuples, each containing
#   - the dictionary key and
#   - regex string for each field
def populate_assets(path, asset_list):
    # Populate list of assets at path
    files = os.listdir(path)

    # Create container for asset entries
    assets = []

    # Initialise field paths as None
    fields = {}
    for item in asset_list:
        fields.update({item[0]: None})

    # Search through each file in folder to try to find raw and mask image paths
    for file in files:
        for item in asset_list:
            result = re.search(item[1], file, re.I)
            if result is not None:
                fields.update({item[0]: os.path.join(path, file)})

    # If we have a mandatory field (first field listed in asset_list)
    if fields[asset_list[0][0]] is not None:
        assets.append(fields)

    # Populate list of subdirectories at path
    subdirs = sorted([x for x in files if os.path.isdir(os.path.join(path, x))])

    # For each subdirectory, recursively populate assets
    for subdir in subdirs:
        assets += populate_assets(os.path.join(path, subdir), asset_list)

    return assets

def main():
    # Make UV map
    generate_uv.main()

    ##############################################
    ##              ASSET LOADING               ##
    ##############################################

    # Populate list of hdr scenes
    print("[INFO] Importing environments from '{0}'".format(scene_cfg.scene_hdr['path']))
    hdrs = populate_assets(
        scene_cfg.scene_hdr['path'], [
            ('raw_path', scene_cfg.HDRI_RAW_REGEX),
            ('mask_path', scene_cfg.HDRI_MASK_REGEX),
        ]
    )
    print("[INFO] Number of environments imported: {0}".format(len(hdrs)))

    # Make sure we're only loading .hdr files
    hdr_index = 0
    hdr = hdrs[hdr_index]

    # Create container for ball entries
    print("[INFO] Importing balls from '{0}'".format(scene_cfg.ball['ball_dir']))
    balls = populate_assets(
        scene_cfg.ball['ball_dir'],
        [
            ('colour_path', scene_cfg.BALL_COL_REGEX),
            ('norm_path', scene_cfg.BALL_NORM_REGEX),
            ('mesh_path', scene_cfg.BALL_MESH_REGEX),
        ],
    )
    print("[INFO] Number of balls imported: {0}".format(len(balls)))

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
    world = env.setup_hdri_env(hdr['raw_path'])

    # Setup render layers (visual, segmentation and field lines)
    render_layer_toggle = env.setup_segmentation_render_layers(len(scene_cfg.classes))

    ##############################################
    ##            SCENE CONSTRUCTION            ##
    ##############################################

    # Construct our default UV sphere ball
    ball = Ball(
        'Ball',
        scene_cfg.classes['ball']['index'],
        curr_ball_info,
    )
    ball.move((0., 0., scene_cfg.ball['radius']))

    # Construct our goals
    goals = [Goal(scene_cfg.classes['goal']['index']), Goal(scene_cfg.classes['goal']['index'])]
    goals[0].offset((scene_cfg.field['length'] / 2., 0., 0.))

    goals[1].offset(
        (-scene_cfg.field['length'] / 2. - 1.5 * scene_cfg.goal['depth'] + scene_cfg.goal['post_width'], 0., 0.)
    )
    goals[1].rotate((0., 0., pi))

    # Construct our grass field
    field = Field(scene_cfg.classes['field']['index'])

    # Construct cameras
    cam_separation = 0 if out_cfg.output_stereo == False else scene_cfg.camera['stereo_cam_dist']
    height = rand.uniform(
        scene_cfg.camera['limits']['position']['z'][0], scene_cfg.camera['limits']['position']['z'][1]
    )

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
    env_batch_size = ceil(out_cfg.num_images / len(hdrs))

    # Batch size for each ball in each HDRI environment map
    ball_batch_size = ceil(env_batch_size / len(balls))

    for frame_num in range(0, out_cfg.num_images):
        # Each ball gets even number of frames for each environment
        if frame_num > 0 and frame_num % ball_batch_size == 0:
            if ball_index + 1 < len(balls):
                ball_index += 1
            curr_ball_info = balls[ball_index]
            # If we're using same UV sphere and only changing textures,
            #   recreating the UV sphere is unnecessary
            if curr_ball_info['mesh_path'] is None and ball.mesh_path is None:
                ball.update_texture(curr_ball_info['colour_path'], curr_ball_info['norm_path'])
            # If we're changing meshes, completely reconstruct our ball
            else:
                ball.construct(curr_ball_info)
            cam_l.set_tracking_target(ball.obj)

        # Each environment map gets even distribution of frames
        if frame_num % env_batch_size == 0:
            ball_index = 0
            if hdr_index + 1 < len(hdrs):
                hdr_index += 1
            hdr = hdrs[hdr_index]
            cam_l.set_tracking_target(ball.obj)

        ## Update ball
        # Move ball
        ball.move((
            rand.uniform(ball_limits['position']['x'][0], ball_limits['position']['x'][1]),
            rand.uniform(ball_limits['position']['y'][0], ball_limits['position']['y'][1]),
            rand.uniform(ball_limits['position']['z'][0], ball_limits['position']['z'][1]),
        ))
        # Rotate ball
        ball.rotate((
            rand.uniform(ball_limits['rotation']['pitch'][0], ball_limits['rotation']['pitch'][1]) * DEG_TO_RAD,
            rand.uniform(ball_limits['rotation']['yaw'][0], ball_limits['rotation']['yaw'][1]) * DEG_TO_RAD,
            rand.uniform(ball_limits['rotation']['roll'][0], ball_limits['rotation']['roll'][1]) * DEG_TO_RAD,
        ))

        ## Update camera
        # Move camera
        cam_l.move((
            rand.uniform(cam_limits['position']['x'][0], cam_limits['position']['x'][1]),
            rand.uniform(cam_limits['position']['y'][0], cam_limits['position']['y'][1]),
            rand.uniform(cam_limits['position']['z'][0], cam_limits['position']['z'][1]),
        ))

        cam_l.rotate((
            rand.uniform(cam_limits['rotation']['pitch'][0], cam_limits['rotation']['pitch'][1]),
            rand.uniform(cam_limits['rotation']['yaw'][0], cam_limits['rotation']['yaw'][1]),
            rand.uniform(cam_limits['rotation']['roll'][0], cam_limits['rotation']['roll'][1]),
        ))

        # Move potential camera target
        a.move((
            rand.uniform(cam_limits['position']['x'][0], cam_limits['position']['x'][1]),
            rand.uniform(cam_limits['position']['y'][0], cam_limits['position']['y'][1]),
            rand.uniform(cam_limits['position']['z'][0], cam_limits['position']['z'][1]),
        ))

        # Focus to goal if within second third of images
        if int(frame_num % env_batch_size) == int(env_batch_size / 3.):
            goal_index = rand.randint(0, 1)
            cam_l.set_tracking_target(goals[goal_index].obj)
        # Focus on random field if within third third of images
        elif int(frame_num % env_batch_size) == int((2 * env_batch_size) / 3.):
            cam_l.set_tracking_target(a.obj)

        # TODO: Update scene to rectify rotation and location matrices

        ##############################################
        ##                RENDERING                 ##
        ##############################################

        filename = '{0:010}'.format(frame_num)

        # Establish camera list for either stereo or mono output
        cam_list = None
        if not out_cfg.output_stereo:
            cam_list = [{'obj': cam_l.obj, 'str': ''}]
        else:
            cam_list = [{'obj': cam_l.obj, 'str': '_L'}, {'obj': cam_r.obj, 'str': '_R'}]

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
            env.update_hdri_env(world, hdr['raw_path'])
            bpy.data.scenes['Scene'].render.filepath = os.path.join(out_cfg.image_dir, filename + cam['str'])
            bpy.ops.render.render(write_still=True)

            ## Mask image rendering
            # Turn on all render layers
            for l in render_layers:
                l.use = True

            # Render mask image
            render_layers['RenderLayer'].use = False
            render_layer_toggle.check = True
            env.update_hdri_env(world, hdr['mask_path'])
            bpy.data.scenes['Scene'].render.filepath = os.path.join(out_cfg.mask_dir, filename + cam['str'])
            bpy.ops.render.render(write_still=True)

if __name__ == '__main__':
    main()
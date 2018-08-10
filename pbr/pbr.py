#!/usr/local/blender -P

import os
import sys
import random as rand
import bpy
import re
import json

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

import util

DEG_TO_RAD = pi / 180.

def main():
    # Make UV map
    # generate_uv.main()

    ##############################################
    ##              ASSET LOADING               ##
    ##############################################

    hdr_index = 0
    ball_index = 0
    hdrs, balls = util.load_assets()

    ##############################################
    ##             ENVIRONMENT SETUP            ##
    ##############################################

    render_layer_toggle, world = util.setup_environment(hdrs[0])

    ##############################################
    ##            SCENE CONSTRUCTION            ##
    ##############################################

    # Construct our default UV sphere ball
    ball = Ball(
        'Ball',
        scene_cfg.classes['ball']['index'],
        balls[0],
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

    # Print information regarding expected scene update performance
    print(
        '[INFO] Environment map update every {0} frame(s), Ball update every {1} frame(s) per environment map, '.format(
            env_batch_size,
            ball_batch_size,
        )
    )

    for frame_num in range(0, out_cfg.num_images):
        # Each ball gets even number of frames for each environment
        if frame_num % ball_batch_size == 0:
            ball_data = balls[ball_index]
            # If we're using same UV sphere and only changing textures,
            #   recreating the UV sphere is unnecessary
            if 'mesh_path' in ball_data and ball_data['mesh_path'] is None and ball.mesh_path is None:
                ball.update_texture(ball_data['colour_path'], ball_data['norm_path'])
            # If we're changing meshes, completely reconstruct our ball
            else:
                ball.construct(ball_data)
            cam_l.set_tracking_target(ball.obj)
            # Update ball index for next pass
            if ball_index + 1 < len(balls):
                ball_index += 1

        # Each environment map gets even distribution of frames
        if frame_num % env_batch_size == 0:
            ball_index = 0
            hdr_data = hdrs[hdr_index]
            cam_l.set_tracking_target(ball.obj)
            # Toggle objects based on environment map requirements
            with open(hdr_data['info_path'], 'r') as f:
                env_info = json.load(f)
            ball.obj.hide_render = not env_info['to_draw']['ball']
            goals[0].obj.hide_render = not env_info['to_draw']['goal']
            goals[1].obj.hide_render = not env_info['to_draw']['goal']
            field.obj.hide_render = not env_info['to_draw']['field']
            field.lower_plane.hide_render = not env_info['to_draw']['field']
            # Update hdr index for next pass
            if hdr_index + 1 < len(hdrs):
                hdr_index += 1

        print(
            '[INFO] Frame {0}: ball: "{1}", map: "{2}"'.format(
                frame_num, os.path.basename(ball_data['colour_path']), os.path.basename(hdr_data['raw_path'])
            )
        )

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
            rand.uniform(cam_limits['rotation']['pitch'][0], cam_limits['rotation']['pitch'][1]) * DEG_TO_RAD,
            rand.uniform(cam_limits['rotation']['yaw'][0], cam_limits['rotation']['yaw'][1]) * DEG_TO_RAD,
            rand.uniform(cam_limits['rotation']['roll'][0], cam_limits['rotation']['roll'][1]) * DEG_TO_RAD,
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
        bpy.context.scene.update()

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
            ball.sc_plane.hide_render = False
            env.update_hdri_env(world, hdr_data['raw_path'])
            bpy.data.scenes['Scene'].render.filepath = os.path.join(out_cfg.image_dir, filename + cam['str'])
            bpy.ops.render.render(write_still=True)

            ## Mask image rendering
            # Turn on all render layers
            for l in render_layers:
                l.use = True

            # Render mask image
            render_layers['RenderLayer'].use = False
            render_layer_toggle.check = True
            ball.sc_plane.hide_render = True
            env.update_hdri_env(world, hdr_data['mask_path'])
            bpy.data.scenes['Scene'].render.filepath = os.path.join(out_cfg.mask_dir, filename + cam['str'])
            bpy.ops.render.render(write_still=True)

if __name__ == '__main__':
    main()
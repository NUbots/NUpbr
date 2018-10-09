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

# TODO: Reimplement field uv generation with Scikit-Image

import util

def main():
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
    anch = CameraAnchor()

    # Alias camera limits for useability
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

    # Default tracking target to ball
    tracking_target = ball.obj

    ##############################################
    ##               SCENE UPDATE               ##
    ##############################################

    for frame_num in range(1, out_cfg.num_images + 1):
        # Each ball gets even number of frames for each environment
        # Set new ball every <ball_batch_size> frames
        if frame_num % ball_batch_size == 0:
            ball_data = balls[ball_index]
            # If we're using same UV sphere and only changing textures,
            #   recreating the UV sphere is unnecessary
            if 'mesh_path' in ball_data and ball_data['mesh_path'] is None and ball.mesh_path is None:
                ball.update_texture(ball_data['colour_path'], ball_data['norm_path'])
            else:
                # If we're changing meshes, completely reconstruct our ball
                ball.construct(ball_data)
            # Update ball index for next pass
            if ball_index + 1 < len(balls):
                ball_index += 1
            tracking_target = ball.obj

        # Each environment map gets even distribution of frames
        # Set new env map every <env_batch_size> frames
        if frame_num % env_batch_size == 0:
            ball_index = 0
            hdr_data = hdrs[hdr_index]
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
            tracking_target = ball.obj

        # Update location and rotation of camera focus and camera
        util.update_scene(ball, cam_l, anch, env_info)

        # Calculate number of frames per object (e.g. 3 for synthetic balls, goals and random)
        num_frames_per_object = float(1 + len([o for o in env_info['to_draw'].values() if o == True]))

        # Focus on ball if within first third of images
        if env_info['to_draw']['ball'] and frame_num < int(out_cfg.num_images / num_frames_per_object):
            tracking_target = ball.obj
        # Focus to goal if within second third of images
        elif env_info['to_draw']['goal'] and frame_num < int(2 * out_cfg.num_images / num_frames_per_object):
            tracking_target = goals[rand.randint(0, 1)].obj
        # Focus on random field if within last third of images
        else:
            tracking_target = anch.obj

        print(
            '[INFO] Frame {0}: ball: "{1}", map: "{2}", target: {3}'.format(
                frame_num,
                os.path.basename(ball_data['colour_path']),
                os.path.basename(hdr_data['raw_path']),
                tracking_target.name,
            )
        )

        cam_l.set_tracking_target(tracking_target)

        # Updates scene to rectify rotation and location matrices
        bpy.context.scene.update()

        ##############################################
        ##                RENDERING                 ##
        ##############################################

        filename = str(frame_num).zfill(out_cfg.filename_len)

        # Render for the main camera only
        bpy.context.scene.camera = cam_l.obj

        # Use multiview stereo if stereo output is enabled
        # (this will automatically render the second camera)
        if out_cfg.output_stereo:
            bpy.context.scene.render.use_multiview = True

        # Render raw image
        util.render_image(
            isMaskImage=False,
            toggle=render_layer_toggle,
            ball=ball,
            world=world,
            env=env,
            hdr_path=hdr_data['raw_path'],
            output_path=os.path.join(out_cfg.image_dir, '{}.png'.format(filename)),
        )

        # Render mask image
        util.render_image(
            isMaskImage=True,
            toggle=render_layer_toggle,
            ball=ball,
            world=world,
            env=env,
            hdr_path=hdr_data['mask_path'],
            output_path=os.path.join(out_cfg.mask_dir, '{}.png'.format(filename)),
        )

if __name__ == '__main__':
    main()
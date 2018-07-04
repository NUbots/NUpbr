#!/usr/local/blender -P

import os
import sys
import random as rand

# Add our current position to path to include package
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

from math import pi, sqrt

from config import scene_config as scene_cfg

from scene import environment as env
from scene.ball import Ball
from scene.field import Field
from scene.goal import Goal
from scene.camera import Camera
from scene.camera_anchor import CameraAnchor

# from field_uv import generate_uv

def main():
    # Make UV map
    # generate_uv.main()

    ##############################################
    ##                  ASSETS                  ##
    ##############################################

    # Populate list of hdr scenes
    scene_hdrs = os.listdir(scene_cfg.scene_hdr['path'])
    # Populate list of ball images and meshes
    uv_maps = os.listdir(scene_cfg.ball['uv_path'])

    # Make sure we're only loading .hdr files
    scene_hdrs = [x for x in scene_hdrs if x[x.rfind('.'):] == '.hdr']
    hdr_path = os.path.join(scene_cfg.scene_hdr['path'], scene_hdrs[rand.randint(0, len(scene_hdrs) - 1)])

    # Ensure only .jpg or .png files are read
    # TODO: Move check to ball class where ball will be constructed depending on import type
    uv_maps = [x for x in uv_maps if x[x.rfind('.'):] in scene_cfg.ball['uv_img_types']]
    ball_path = os.path.join(scene_cfg.ball['uv_path'], uv_maps[rand.randint(0, len(uv_maps) - 1)])

    ##############################################
    ##                ENVIRONMENT               ##
    ##############################################

    # Clear default environment
    env.clear_env()
    # Setup render settings
    env.setup_render()
    # Setup HRDI environment
    env.setup_hdri_env(hdr_path)

    # Setup render layers (visual, segmentation and field lines)
    env.setup_segmentation_render_layers(len(scene_cfg.classes))

    ##############################################
    ##                  SCENE                   ##
    ##############################################

    # Construct camera anchor
    a = CameraAnchor()
    a.move((0., 0., scene_cfg.ball['radius']))

    # Construct cameras (requires camera anchor object as parent)
    cam_l = Camera('Camera_L')
    cam_l.rotate((45. * (pi / 180.), 0., 0.))
    cam_l.move((-scene_cfg.camera['stereo']['cam_dist'] / 2., -(1. / sqrt(2)), 1. / sqrt(2)))

    cam_r = Camera('Camera_R')
    cam_r.rotate((45. * (pi / 180.), 0., 0.))
    cam_r.move((scene_cfg.camera['stereo']['cam_dist'] / 2., -(1. / sqrt(2)), 1. / sqrt(2)))

    # Anchor cameras to anchor point
    cam_l.anchor(a.obj)
    cam_r.anchor(a.obj)

    # Construct our ball in class 1
    b = Ball('Ball', scene_cfg.classes['ball']['index'], ball_path)
    b.move((0., 0., scene_cfg.ball['radius']))

    # Construct our goals both in class 2
    g = [Goal(scene_cfg.classes['goal']['index']), Goal(scene_cfg.classes['goal']['index'])]
    g[0].offset((scene_cfg.field['length'] / 2., 0., 0.))

    g[1].offset(
        (-scene_cfg.field['length'] / 2. - 1.5 * scene_cfg.goal['depth'] + scene_cfg.goal['post_width'], 0., 0.)
    )
    g[1].rotate((0., 0., pi))

    # Construct our grass field in class 3 (where field lines will be class 4)
    f = Field(scene_cfg.classes['field']['index'])

    ##############################################
    ##                  RENDER                  ##
    ##############################################

if __name__ == '__main__':
    main()
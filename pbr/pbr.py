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

    # Populate list of hdr scenes
    scene_hdrs = os.listdir(scene_cfg.scene_hdr['path'])
    # Make sure we're only loading .hdr files
    scene_hdrs = [x for x in scene_hdrs if x[x.rfind('.'):] == '.hdr']
    img_path = os.path.join(scene_cfg.scene_hdr['path'], scene_hdrs[rand.randint(0, len(scene_hdrs) - 1)])

    # Clear default environment
    env.clear_env()
    # Setup render settings
    env.setup_render()
    # Setup HRDI environment
    env.setup_hdri_env(img_path)

    # Setup render layers (visual, segmentation and field lines)
    env.setup_segmentation_render_layers(len(scene_cfg.classes))

    # Construct camera anchor
    a = CameraAnchor()
    a.move((0., 0., scene_cfg.ball['radius']))

    # Construct camera (requires camera anchor object as parent)
    c = Camera(a.obj)
    c.rotate((45. * (pi / 180.), 0., 0.))
    c.move((0., -(1. / sqrt(2)), 1. / sqrt(2)))

    # Construct our ball in class 1
    b = Ball(scene_cfg.classes['ball']['index'])
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

if __name__ == '__main__':
    main()
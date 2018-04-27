#!/usr/local/blender -P

import os
import sys

# TODO: Remove hacky include
# Add our current position to path to include our config files
sys.path.insert(0, '.')
sys.path.insert(0, os.path.join('..', 'field_uv'))

import scene_config as scene_cfg

from math import pi

from scene import environment as env
from scene.ball import Ball
from scene.field import Field
from scene.goal import Goal
from scene.camera import Camera

def main():
    # Clear default environment
    env.clear_env()
    # Setup render settings
    env.setup_render()
    # Setup HRDI environment
    env.setup_hdri_env()

    # Setup class indices
    classes = ['ball', 'goal', 'field']

    # Setup render layers (visual, segmentation and field lines)
    env.setup_segmentation_render_layers(len(classes))

    # Construct camera
    c = Camera()

    # Construct our ball in class 1
    b = Ball(1)

    # Construct our goals both in class 2
    g = [Goal(2), Goal(2)]
    g[0].move((scene_cfg.field['length'] / 2., 0., 0.))

    g[1].move((-scene_cfg.field['length'] / 2. - 1.5 * scene_cfg.goal['depth'] + scene_cfg.goal['post_width'], 0., 0.))
    g[1].rotate((0., 0., pi))

    # Construct our grass field in class 3 (where field lines will be class 4)
    f = Field(3)

if __name__ == '__main__':
    main()
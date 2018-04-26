#!/usr/local/blender -P

import sys

# TODO: Remove hacky include
# Add our current position to path to include our config files
sys.path.insert(0, '.')
sys.path.insert(0, '../field_uv_generation')

import environment as env
import scene_config as scene_cfg

from math import pi
from field import Field
from ball import Ball
from goal import Goal

def main():
    # Clear default environment
    env.clear_env()
    # Setup render settings
    env.setup_render()
    # Setup HRDI environment
    env.setup_hdri_env()

    classes = ['ball', 'goal', 'field']

    env.setup_segmentation_render_layers(len(classes))

    # Construct our grass field
    f = Field(3)
    f.construct_field()

    # Construct our ball
    b = Ball(1)
    b.construct_ball()

    # Construct our goals
    g = [Goal(2), Goal(2)]
    g[0].construct_goal()
    g[0].move_goal((scene_cfg.field['length'] / 2., 0., 0.))

    g[1].construct_goal()
    g[1].move_goal(
        (-scene_cfg.field['length'] / 2. - 1.5 * scene_cfg.goal['depth'] + scene_cfg.goal['post_width'], 0., 0.)
    )
    g[1].rotate_goal((0., 0., pi))

if __name__ == '__main__':
    main()
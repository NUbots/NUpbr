#!C:\"Program Files"\"Blender Foundation"\Blender\blender -P

import sys

# TODO: Remove hacky include
# Add our current position to path to include our config files
sys.path.insert(0, '.')
sys.path.insert(0, '../field_uv_generation')

import environment as env
import scene_config as scene_cfg

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

    # Construct our grass field
    f = Field()
    f.construct_field()

    # Construct our ball
    b = Ball()
    b.construct_ball()

    # Construct our goals
    g = [Goal(), Goal()]
    g[0].construct_goal()
    g[0].move_goal((scene_cfg.field['length'] / 2., 0., 0.))

    g[1].construct_goal()
    g[1].move_goal((-scene_cfg.field['length'] / 2., 0., 0.))

if __name__ == '__main__':
    main()
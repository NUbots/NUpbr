#!C:\"Program Files"\"Blender Foundation"\Blender\blender -P

import os
import sys
import bpy

# TODO: Remove hacky include
# Add our current position to path to include our config files
sys.path.insert(0, '.')

from field import Field
from ball import Ball
from goal import Goal
import environment as env

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
    # g = Goal()

if __name__ == '__main__':
    main()
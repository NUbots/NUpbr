from math import pi
from os import path

### Configuration File for Generation of Soccer Field UV Map ###
# (All measurements in metres)

field = {
    'length': 9,
    'width': 6,
    'goal_area': {
        'length': 1,
        'width': 5
    },
    'penalty_mark_dist': 2.1,
    'centre_circle_radius': 0.75,
    'border_width': 0.7,
    'field_line_width': 0.05,
    'grass_height': 0.033,
}

goal = {
    'depth': 0.6,
    'width': 2.6,
    'height': 1.8,
    'post_width': 0.12,
    'shape': 'circular',
}

ball = {
    'radius': 0.5969 / (2 * pi),
}

camera = {
    'focal_length': 0,
}

image = {
    'type': '.png',
    'mode': 'RGBA',
    'pixels_per_metre': 100,
    'path': path.abspath(path.join('..', 'uv')),
    'name': 'default',
    'orientation': 'portrait',
}
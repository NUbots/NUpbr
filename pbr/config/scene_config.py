# Field-specific Configuration Settings
#   * All measurements are in metres

from math import pi
from os import path, pardir

# Get project path
proj_path = path.abspath(path.join(path.join(path.dirname(path.realpath(__file__)), pardir), pardir))

classes = {
    'unclassified': {
        'index': 0,
        'colour': (0., 0., 0., 1.)
    },
    'ball': {
        'index': 1,
        'colour': (1., 0., 0., 1.)
    },
    'field': {
        'index': 2,
        'colour': (0., 1., 0., 1.),
        'field_lines_colour': (1., 1., 1., 1.)
    },
    'goal': {
        'index': 3,
        'colour': (1., 1., 0., 1.)
    },
}

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
    'net_height': 1.2,
}

ball = {
    'radius': 0.5969 / (2 * pi),
    'uv_img_types': [
        '.jpg',
        '.png',
    ],
    'uv_path': path.abspath(path.join(path.join(proj_path, 'resources'), 'ball_uv')),
}

camera = {
    'type': 'PANO',
    'cycles': {
        'type': 'FISHEYE'
    },
    'focal_length': 10.5,
    'fov': pi,
}

field_uv = {
    'type': '.png',
    'mode': 'RGBA',
    'pixels_per_metre': 100,
    'uv_path': path.abspath(path.join(path.join(proj_path, 'resources'), 'field_uv')),
    'name': 'default',
    'orientation': 'portrait',
}

scene_hdr = {
    'path': path.abspath(path.join(path.join(proj_path, 'resources'), 'scene_hdr')),
}
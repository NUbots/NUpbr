# Field-specific Configuration Settings
#   * All measurements are in SI units

from math import pi
from os import path, pardir
import random
import colorsys
import numpy as np

# Get project path
proj_path = path.abspath(
    path.join(path.join(path.dirname(path.realpath(__file__)), pardir), pardir)
)

# Create resource path
res_path = path.join(proj_path, "resources")

# Dictate how many randomly generated shape objects there will be
num_shapes = 8

# Number of robots to fill the scene
num_robots = 3
num_misc_robots = 3

# The radius that defines the personal space of a robot
robot_radius = 0.7

# Field dimensions
field_dims = {
    "length": 9,
    "width": 6,
    "goal_area": {"length": 1, "width": 5},
    "penalty_mark_dist": 2.1,
    "centre_circle_radius": 0.75,
    "border_width": 0.7,
    "field_line_width": 0.05,
    "grass_height": random.uniform(0.02, 0.05),
}

resources = {
    "robot": {
        "mesh_path": path.abspath(path.join(res_path, "robot", "NUgus_esh.fbx")),
        "texture_path": path.abspath(path.join(res_path, "robot", "textures")),
        "kinematics_path": path.abspath(path.join(res_path, "robot", "NUgus_esh.json")),
        "kinematics_variance": 0.5,  ## Determines how much variance the random poses will have
        "mask": {"index": 3, "colour": (0, 0, 1, 1)},
    },
    "misc_robot": {
        "robot_list": {
            "darwin": {
                "mesh_path": path.abspath(path.join(res_path, "robot", "darwin_fixed.fbx")),
                "kinematics_path": path.abspath(path.join(res_path, "robot", "darwin_fixed.json")),
                "kinematics_variance": 0.5
            }},
        "mask": {"index": 3, "colour": (0, 0, 1, 1)},
    },

    "ball": {
        "img_types": [".jpg", ".png"],
        "mesh_types": [".fbx", ".obj"],
        "path": path.abspath(path.join(res_path, "balls")),
        "mask": {"index": 1, "colour": (1, 0, 0, 1)},
    },
    "environment": {
        "path": path.abspath(path.join(res_path, "hdr")),
        "hdri_types": [".hdr"],
        "mask_types": [".png"],
        "info_type": ".json",
        "mask": {"index": 0, "colour": (0, 0, 0, 1)},
    },
    ## Always make sure that the field has the last index so field lines can be index + 1
    "field": {
        "type": ".png",
        "mode": "RGBA",
        "pixels_per_metre": 100,
        "uv_path": path.abspath(path.join(res_path, "field_uv")),
        "grass": {
            "path": path.abspath(path.join(res_path, "grass")),
            "img_types": [".jpg", ".png"],
        },
        "name": "default",
        "orientation": "portrait",
        "mask": {"index": 4, "colour": (0, 1, 0, 1), "line_colour": (1, 1, 1, 1)},
    },
    "goal": {"mask": {"index": 2, "colour": (1, 1, 0, 1)}},
}

def new_misc_robot():
    mesh_path = ''.join(path.abspath(path.join(res_path, "robot", random.choice(resources["misc_robot"]["robot_list"]))))
    return mesh_path

def choose_misc_robot():
    choice = random.choice(list(resources["misc_robot"]["robot_list"].keys()))
    #return choice
    return resources["misc_robot"]["robot_list"][choice]

def get_misc_robot(robot_path):
    #robot = resources["misc_robot"]["robot_list"][path]["mesh_path"]

    mesh_path = ''.join(path.abspath(path.join(res_path, "robot", resources["misc_robot"]["robot_list"][robot_path]["mesh_path"])))
    return mesh_path

def configure_scene():

    ball_radius = 0.5969 / (2 * pi)

    cfg = {}

    # Add environment information
    cfg.update({"environment": {"strength": random.uniform(0.5, 2)}})

    # Add field information
    cfg.update(
        {
            "field": {
                "length": 9,
                "width": 6,
                "goal_area": {"length": 1, "width": 5},
                "penalty_mark_dist": 2.1,
                "centre_circle_radius": 0.75,
                "border_width": 0.7,
                "field_line_width": 0.05,
                "grass_height": random.uniform(0.02, 0.05),
            }
        }
    )

    # Add ball information
    cfg.update(
        {
            "ball": {
                "radius": ball_radius,
                "auto_position": True,
                "position": (
                    random.uniform(
                        -cfg["field"]["length"] * 0.5, cfg["field"]["length"] * 0.5
                    ),
                    random.uniform(
                        -cfg["field"]["width"] * 0.5, cfg["field"]["width"] * 0.5
                    ),
                    ball_radius,
                ),
                "rotation": (
                    random.uniform(-pi, pi),
                    random.uniform(-pi, pi),
                    random.uniform(-pi, pi),
                ),
            }
        }
    )

    # Add goal information
    cfg.update(
        {
            "goal": {
                "depth": 0.6,
                "width": 2.6,
                "height": 1.8,
                "post_width": 0.12,
                "shape": random.choice(["circular", "square"]),
                "net_height": 1.2,
            }
        }
    )

    # Add camera information
    cfg.update(
        {
            "camera": {
                **random.choice(
                    [
                        {"type": "EQUISOLID", "focal_length": 10.5, "fov": pi},
                        {"type": "RECTILINEAR", "fov": 0.857},
                    ]
                ),
                "stereo_camera_distance": 0.1,
            }
        }
    )

    # Add anchor information
    cfg.update(
        {
            "anchor": {
                "position": (
                    random.uniform(
                        -cfg["field"]["length"] * 0.5, cfg["field"]["length"] * 0.5
                    ),
                    random.uniform(
                        -cfg["field"]["width"] * 0.5, cfg["field"]["width"] * 0.5
                    ),
                    0,
                )
            }
        }
    )

    cfg.update(
        {
            "shape": [
                {
                    "dimensions": (
                        random.uniform(0.05, 0.5),
                        random.uniform(0.05, 0.5),
                        random.uniform(0.05, 0.5),
                    ),
                    "position": (
                        random.uniform(
                            -cfg["field"]["length"] * 0.5, cfg["field"]["length"] * 0.5
                        ),
                        random.uniform(
                            -cfg["field"]["width"] * 0.5, cfg["field"]["width"] * 0.5
                        ),
                        random.uniform(0.2, 0.5),
                    ),
                    "rotation": (
                        random.uniform(-pi, +pi),
                        random.uniform(-pi, +pi),
                        random.uniform(-pi, +pi),
                    ),
                    "material": {
                        "base_col": colorsys.hsv_to_rgb(
                            random.uniform(0.440, 1.174),
                            random.uniform(0.0, 1.0),
                            random.uniform(0.0, 1.0),
                        ),
                        "metallic": random.uniform(0.0, 1.0),
                        "roughness": random.uniform(0.0, 1.0),
                    },
                }
                for ii in range(num_shapes)
            ]
        }
    )

    # Add robot information
    cfg.update(
        {
            "robot": [
                {
                    "auto_position": True,
                    # Defines possible random placement range of x, y and z positional components
                    "position": (
                        random.uniform(
                            -cfg["field"]["length"] * 0.5,
                            cfg["field"]["length"] * 0.5,
                        ),
                        random.uniform(
                            -cfg["field"]["width"] * 0.5, cfg["field"]["width"] * 0.5
                        ),
                        random.uniform(0.5, 0.5),
                    ),
                }
                for ii in range(num_robots + 1)
            ]
        }
    )

    # Add robot information
    cfg.update(
        {
            "misc_robot": [
                {
                    "auto_position": True,
                    # Defines possible random placement range of x, y and z positional components
                    "position": (
                        random.uniform(
                            -cfg["field"]["length"] * 0.5, cfg["field"]["length"] * 0.5
                        ),
                        random.uniform(
                            -cfg["field"]["width"] * 0.5, cfg["field"]["width"] * 0.5
                        ),
                        random.uniform(0.45, 0.5),
                    ),
                    "rotation": (
                        0, 0, random.uniform(0, 359),
                    ),
                }
                for ii in range(num_misc_robots)
            ]
        }
    )

    # Add anchor information
    cfg.update(
        {
            "anchor": {
                "position": (
                    random.uniform(
                        -cfg["field"]["length"] * 0.5, cfg["field"]["length"] * 0.5
                    ),
                    random.uniform(
                        -cfg["field"]["width"] * 0.5, cfg["field"]["width"] * 0.5
                    ),
                    0,
                )
            }
        }
    )

    return cfg

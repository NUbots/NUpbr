import os
import re
import bpy
import random as rand
import numpy as np
import math
import cv2

from config import scene_config
from scene import environment as env

# Get a list of files and directores in the given path
# as a tuple with (files, directories)
def list_files_and_dirs(path, absolute=False):
    files = []
    dirs = []

    for child in os.listdir(path):
        child_path = os.path.join(path, child)
        if os.path.isdir(child_path):
            dirs.append(child_path if absolute else child)
        else:
            files.append(child_path if absolute else child)

    return (files, dirs)


# Populate the given assets list with assets from path as defined by asset_fields
# Where asset_fields is a list of two-tuples, each containing
#   - the field's dictionary key and
#   - the field's regex string
def populate_assets(assets, path, asset_fields):
    # Get the files and folders at the given path
    files, subdirs = list_files_and_dirs(path, absolute=True)

    # Initialise asset with fields as None
    asset = {}
    for field in asset_fields:
        asset.update({field[0]: None})

    # Search through each file and add them to the asset if they match an asset field
    for file_path in files:
        for field_name, field_re in asset_fields:
            if re.search(field_re, file_path, re.I) is not None:
                asset.update({field_name: file_path})

    # Add the asset if the first field (the mandatory one) has a file
    if asset[asset_fields[0][0]] is not None:
        assets.append(asset)

    # For each subdirectory, recursively populate assets
    for subdir in sorted(subdirs):
        populate_assets(assets, subdir, asset_fields)

    return assets


# Load ball and HDR map data from respective paths,
#   traversing recursively through subdirectories
def load_assets():
    resources = scene_config.resources

    ball_img_ext = "(?:{})$".format(
        "|".join([re.escape(s) for s in resources["ball"]["img_types"]])
    )
    ball_mesh_ext = "(?:{})$".format(
        "|".join([re.escape(s) for s in resources["ball"]["mesh_types"]])
    )
    ball_norm_re = r"norm(?:al)?s?.*" + ball_img_ext
    ball_colour_re = r"colou?rs?.*" + ball_img_ext
    ball_mesh_re = ball_mesh_ext

    print("[INFO] Importing balls from '{0}'".format(resources["ball"]["path"]))
    balls = populate_assets(
        [],
        resources["ball"]["path"],
        [
            ("colour_path", ball_colour_re),
            ("norm_path", ball_norm_re),
            ("mesh_path", ball_mesh_re),
        ],
    )
    print("[INFO] \tNumber of balls imported: {0}".format(len(balls)))

    env_raw_ext = "(?:{})$".format(
        "|".join([re.escape(s) for s in resources["environment"]["hdri_types"]])
    )
    env_mask_ext = "(?:{})$".format(
        "|".join([re.escape(s) for s in resources["environment"]["mask_types"]])
    )
    env_meta_ext = "{}$".format(re.escape(resources["environment"]["info_type"]))
    env_raw_re = "raw.*" + env_raw_ext
    env_mask_re = "mask.*" + env_mask_ext
    env_meta_re = env_meta_ext

    # Populate list of hdr scenes
    print(
        "[INFO] Importing environments from '{0}'".format(
            resources["environment"]["path"]
        )
    )
    hdrs = populate_assets(
        [],
        resources["environment"]["path"],
        [
            ("raw_path", env_raw_re),
            ("mask_path", env_mask_re),
            ("info_path", env_meta_re),
        ],
    )
    print("[INFO] \tNumber of environments imported: {0}".format(len(hdrs)))

    # Populate list of grass textures
    grass_img_ext = "(?:{})$".format(
        "|".join([re.escape(s) for s in resources["field"]["grass"]["img_types"]])
    )
    grass_diffuse_re = r"diffuse.*" + grass_img_ext
    grass_normal_re = r"normal.*" + grass_img_ext
    grass_bump_re = r"bump.*" + grass_img_ext
    print(
        "[INFO] Importing grass textures from '{0}'".format(
            resources["field"]["grass"]["path"]
        )
    )
    grasses = populate_assets(
        [],
        resources["field"]["grass"]["path"],
        [
            ("diffuse", grass_diffuse_re),
            ("normal", grass_normal_re),
            ("bump", grass_bump_re),
        ],
    )
    print("[INFO] \tNumber of grass textures imported: {0}".format(len(grasses)))

    return hdrs, balls, grasses


def setup_environment(hdr, env_info):
    # Clear default environment
    env.clear_env()
    # Setup render settings
    env.setup_render()
    # Setup HRDI environment
    world = env.setup_hdri_env(hdr["raw_path"], env_info)

    # Setup render layers (visual, segmentation and field lines)
    return env.setup_render_layers(len(scene_config.resources)), world


# Renders image frame for either raw or mask image (defined by <isRawImage>)
def render_image(
    isMaskImage,
    toggle,
    shadowcatcher,
    world,
    env,
    hdr_path,
    strength,
    env_info,
    output_path,
):
    # Turn off all render layers
    for l in bpy.context.scene.render.layers:
        l.use = isMaskImage

    # Enable raw image rendering if required
    bpy.context.scene.render.layers["RenderLayer"].use = not isMaskImage
    toggle[0].check = isMaskImage
    toggle[1].inputs[0].default_value = 1 if isMaskImage else 0
    shadowcatcher.obj.hide_render = isMaskImage
    # Update HDRI map
    env.update_hdri_env(world, hdr_path, env_info)
    bpy.context.scene.world.node_tree.nodes["Background"].inputs[
        "Strength"
    ].default_value = strength
    # Update render output filepath
    bpy.data.scenes["Scene"].render.filepath = output_path
    bpy.ops.render.render(write_still=True)


def matrix_to_list(mat):
    return [
        [mat[0][0], mat[0][1], mat[0][2], mat[0][3]],
        [mat[1][0], mat[1][1], mat[1][2], mat[1][3]],
        [mat[2][0], mat[2][1], mat[2][2], mat[2][3]],
        [mat[3][0], mat[3][1], mat[3][2], mat[3][3]],
    ]


def project_to_ground(y, x, cam_location, img, env_info):
    # Normalise the coordinates into a form useful for making unit vectors
    phi = (y / img.shape[0]) * math.pi
    theta = (0.5 - (x / img.shape[1])) * math.pi * 2
    target_vector = np.array(
        [
            math.sin(phi) * math.cos(theta),
            math.sin(phi) * math.sin(theta),
            math.cos(phi),
        ]
    )

    # Create rotation matrix
    # Roll (x) pitch (y) yaw (z)
    alpha = math.radians(env_info["rotation"]["roll"])
    beta = math.radians(env_info["rotation"]["pitch"])
    gamma = math.radians(env_info["rotation"]["yaw"])

    sa = math.sin(alpha)
    ca = math.cos(alpha)
    sb = math.sin(beta)
    cb = math.cos(beta)
    sg = math.sin(gamma)
    cg = math.cos(gamma)

    rot_x = np.matrix([[1, 0, 0], [0, ca, -sa], [0, sa, ca]])  # yapf: disable
    rot_y = np.matrix([[cb, 0, sb], [0, 1, 0], [-sb, 0, cb]])  # yapf: disable
    rot_z = np.matrix([[cg, -sg, 0], [sg, cg, 0], [0, 0, 1]])  # yapf: disable

    rot = rot_z * rot_y * rot_x

    # Rotate the target vector by the rotation of the environment
    target_vector = target_vector * rot
    target_vector = np.array(
        [target_vector[0, 0], target_vector[0, 1], target_vector[0, 2]]
    )

    # Project the target vector to the ground plane to get a position
    height = -cam_location[2]

    # Get the position for the target
    ground_point = target_vector * (height / target_vector[2])

    # Move into the world coordinates
    ground_point = np.array([ground_point[0], ground_point[1]])

    # Offset x/y by the camera position
    ground_point = ground_point + np.array([cam_location[0], cam_location[1]])

    return (ground_point[0], ground_point[1])


def point_on_field(cam_location, mask_path, env_info, num_points):
    try:
        img = cv2.imread(mask_path)
    except:
        raise NameError("Cannot load image {0}".format(mask_path))

    # Get coordinates where colour is field colour or field line colour
    field_coords = np.stack(
        (
            np.logical_or(
                np.all(
                    img
                    == [
                        [
                            [
                                int(round(v * 255))
                                for v in scene_config.resources["field"]["mask"][
                                    "colour"
                                ][:3][::-1]
                            ]
                        ]
                    ],
                    axis=-1,
                ),
                np.all(
                    img
                    == [
                        [
                            [
                                int(round(v * 255))
                                for v in scene_config.resources["field"]["mask"][
                                    "line_colour"
                                ][:3][::-1]
                            ]
                        ]
                    ],
                    axis=-1,
                ),
            )
        ).nonzero(),
        axis=-1,
    )

    ground_points = []

    # Check if environment map has field points, else set to origin
    if len(field_coords) > 0:
        for ii in range(num_points):
            # Get random field point
            y, x = field_coords[rand.randint(0, field_coords.shape[0] - 1)]

            ground_points.append(project_to_ground(y, x, cam_location, img, env_info))
    return ground_points

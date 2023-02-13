import os
import re
import bpy
import random as rand
import numpy as np
import math
import cv2

from config import scene_config
from scene import environment as env

# Import assets from path as defined by asset_list
# Where asset list ('assets') is a list of two-tuples, each containing
#   - the dictionary key and
#   - regex string for each field
def populate_assets(path, asset_list):
    # Populate list of assets at path
    files = os.listdir(path)

    # Create container for asset entries
    assets = []

    # Initialise field paths as None
    fields = {}
    for item in asset_list:
        fields.update({item[0]: None})

    # Search through each file in folder to try to find raw and mask image paths
    for file in files:
        for item in asset_list:
            result = re.search(item[1], file, re.I)
            if result is not None:
                fields.update({item[0]: os.path.join(path, file)})

    # If we have a mandatory field (first field listed in asset_list)
    if fields[asset_list[0][0]] is not None:
        assets.append(fields)

    # Populate list of subdirectories at path
    subdirs = sorted([x for x in files if os.path.isdir(os.path.join(path, x))])

    # For each subdirectory, recursively populate assets
    for subdir in subdirs:
        assets += populate_assets(os.path.join(path, subdir), asset_list)

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
    for l in bpy.context.scene.view_layers:
        l.use = isMaskImage

    # Enable raw image rendering if required
    bpy.context.scene.view_layers["View Layer"].use = not isMaskImage
    toggle[0].check = isMaskImage
    toggle[1].inputs[0].default_value = 1 if isMaskImage else 0
    shadowcatcher.obj.hide_render = isMaskImage
    # Update HDRI map
    env.update_hdri_env(world, hdr_path, env_info)
    bpy.context.scene.world.node_tree.nodes["Background"].inputs[
        "Strength"
    ].default_value = strength
    # Update render output filepath
    scene = bpy.data.scenes["Scene"]
    scene.render.filepath = output_path

    # Prevent colour transform settings from being applied to the seg image output
    if isMaskImage:
        scene.view_settings.view_transform = "Standard"
    else:
        scene.view_settings.view_transform = "Filmic"

    scene.render.image_settings.color_depth = "16"
    scene.render.image_settings.compression = 0
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
        while len(ground_points) < scene_config.num_robots:
            # Get random field point
            y, x = field_coords[rand.randint(0, field_coords.shape[0] - 1)]
            yproj, xproj = project_to_ground(y, x, cam_location, img, env_info)

            if any(
                [
                    (p[0] - xproj) ** 2 + (p[1] - yproj) ** 2
                    < scene_config.radius_robot**2
                    for p in ground_points
                ]
            ):
                print("Skipping point")
                continue

            ground_points.append(project_to_ground(y, x, cam_location, img, env_info))

    return ground_points


def generate_moves(field_obj, z_coord=0.3, radius=0.7):
    # Use the field dimensions to generate a set of moves, mainly for the robots
    abs_x, abs_y, _ = field_obj.dimensions

    world_points = []

    while len(world_points) < scene_config.num_robots:
        # Get random field point
        point = np.random.uniform(
            low=(-abs_x / 2, -abs_y / 2), high=(abs_x / 2, abs_y / 2)
        )

        if any(
            [
                (p[0] - point[0]) ** 2 + (p[1] - point[1]) ** 2 < radius**2
                for p in world_points
            ]
        ):
            print("Skipping point")
            continue

        world_points.append((*point, z_coord))

    return world_points

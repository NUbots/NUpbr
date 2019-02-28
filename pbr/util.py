import os
import re
import bpy
import random as rand
import numpy as np
import math
import cv2

from config import scene_config as scene_cfg

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
    # Populate list of hdr scenes
    print("[INFO] Importing environments from '{0}'".format(scene_cfg.scene_hdr['path']))
    hdrs = populate_assets(
        scene_cfg.scene_hdr['path'], [
            ('raw_path', scene_cfg.HDRI_RAW_REGEX),
            ('mask_path', scene_cfg.HDRI_MASK_REGEX),
            ('info_path', scene_cfg.HDRI_INFO_REGEX),
        ]
    )
    print("[INFO] \tNumber of environments imported: {0}".format(len(hdrs)))

    # Create container for ball entries
    print("[INFO] Importing balls from '{0}'".format(scene_cfg.ball['ball_dir']))
    balls = populate_assets(
        scene_cfg.ball['ball_dir'],
        [
            ('colour_path', scene_cfg.BALL_COL_REGEX),
            ('norm_path', scene_cfg.BALL_NORM_REGEX),
            ('mesh_path', scene_cfg.BALL_MESH_REGEX),
        ],
    )
    print("[INFO] \tNumber of balls imported: {0}".format(len(balls)))

    return hdrs, balls

def setup_environment(hdr, env_info):
    # Clear default environment
    env.clear_env()
    # Setup render settings
    env.setup_render()
    # Setup HRDI environment
    world = env.setup_hdri_env(hdr['raw_path'], env_info)

    # Setup render layers (visual, segmentation and field lines)
    return env.setup_render_layers(len(scene_cfg.classes)), world

# Renders image frame for either raw or mask image (defined by <isRawImage>)
def render_image(isMaskImage, toggle, ball, world, env, hdr_path, env_info, output_path):
    # Turn off all render layers
    for l in bpy.context.scene.render.layers:
        l.use = isMaskImage

    # Enable raw image rendering if required
    bpy.context.scene.render.layers['RenderLayer'].use = not isMaskImage
    toggle[0].check = isMaskImage
    toggle[1].inputs[0].default_value = 1. if isMaskImage else 0.
    ball.sc_plane.hide_render = isMaskImage
    # Update HDRI map
    env.update_hdri_env(world, hdr_path, env_info)
    # Update render output filepath
    bpy.data.scenes['Scene'].render.filepath = output_path
    bpy.ops.render.render(write_still=True)

# Updates position and rotation for ball, camera and camera anchor objects
def update_scene(ball, cam, anch, env_info, hdr):
    # TODO: Update object limits based on if field/goals are rendered

    # Update camera
    # If we are not drawing the field, use the HDRs camera height
    cam_limits = scene_cfg.camera['limits']
    if not env_info['to_draw']['field']:
        cam_limits['position']['z'][0] = env_info['position']['z']
        cam_limits['position']['z'][1] = env_info['position']['z']
    update_obj(cam, cam_limits)

    # Update ball
    ball_limits = scene_cfg.ball['limits']
    if ball_limits['auto_set_limits'] and not env_info['to_draw']['field']:
        generate_ball_pos(ball, cam, hdr, env_info)
    else:
        update_obj(ball, ball_limits)

    # Update anchor
    update_obj(anch, ball_limits)

# Updates position and rotation by uniform random generation within limits for each component
def update_obj(obj, limits):
    if 'position' in limits:
        obj.move((
            rand.uniform(limits['position']['x'][0], limits['position']['x'][1]),
            rand.uniform(limits['position']['y'][0], limits['position']['y'][1]),
            rand.uniform(limits['position']['z'][0], limits['position']['z'][1]),
        ))
    if 'rotation' in limits:
        obj.rotate((
            math.radians(rand.uniform(limits['rotation']['pitch'][0], limits['rotation']['pitch'][1])),
            math.radians(rand.uniform(limits['rotation']['yaw'][0], limits['rotation']['yaw'][1])),
            math.radians(rand.uniform(limits['rotation']['roll'][0], limits['rotation']['roll'][1])),
        ))

def generate_ball_pos(ball, cam, hdr, env_info):
    try:
        img = cv2.imread(hdr['mask_path'])
    except:
        raise NameError('Cannot load image {0}'.format(hdr['mask_path']))

    # Get coordinates where colour is field colour or field line colour
    field_coords = np.stack(
        (
            np.logical_or(
                np.all(
                    img == [[[int(round(v * 255)) for v in scene_cfg.classes['field']['colour'][:3][::-1]]]],
                    axis=-1,
                ),
                np.all(
                    img == [[[int(round(v * 255)) for v in scene_cfg.classes['field']['field_lines_colour'][:3][::-1]]]
                            ],
                    axis=-1,
                )
            )
        ).nonzero(),
        axis=-1,
    )

    # Get random field point
    y, x = field_coords[rand.randint(0, field_coords.shape[0] - 1)]

    # Normalise the coordinates into a form useful for making unit vectors
    phi = (y / img.shape[0]) * math.pi
    theta = (0.5 - (x / img.shape[1])) * math.pi * 2
    ball_vector = np.array([
        math.sin(phi) * math.cos(theta),
        math.sin(phi) * math.sin(theta),
        math.cos(phi),
    ])

    # Create rotation matrix
    # Roll (x) pitch (y) yaw (z)
    alpha = math.radians(env_info['rotation']['roll'])
    beta = math.radians(env_info['rotation']['pitch'])
    gamma = math.radians(env_info['rotation']['yaw'])

    sa = math.sin(alpha)
    ca = math.cos(alpha)
    sb = math.sin(beta)
    cb = math.cos(beta)
    sg = math.sin(gamma)
    cg = math.cos(gamma)

    rot_x = np.matrix([
        [1,  0,   0],
        [0, ca, -sa],
        [0, sa,  ca],
    ]) # yapf: disable
    rot_y = np.matrix([
        [ cb, 0, sb],
        [  0, 1,  0],
        [-sb, 0, cb],
    ]) # yapf: disable
    rot_z = np.matrix([
        [cg, -sg, 0],
        [sg,  cg, 0],
        [ 0,   0, 1],
    ]) # yapf: disable

    rot = rot_z * rot_y * rot_x

    # Rotate the ball vector by the rotation of the environment
    ball_vector = rot.dot(ball_vector)
    ball_vector = np.array([ball_vector[0, 0], ball_vector[0, 1], ball_vector[0, 2]])

    # Project the ball vector to the ground plane to get a ball position
    height = -cam.obj.location[2]

    # Get the position for the ball
    ground_point = ball_vector * (height / ball_vector[2])

    # Move into the world coordinates
    ground_point = np.array([ground_point[0], ground_point[1], scene_cfg.ball['radius']])

    # Offset x/y by the camera position
    ground_point = ground_point + np.array([cam.obj.location[0], cam.obj.location[1], 0])

    ball.move((ground_point[0], ground_point[1], ground_point[2]))

    # Random rotation
    ball.rotate((
        rand.uniform(-math.pi, math.pi),
        rand.uniform(-math.pi, math.pi),
        rand.uniform(-math.pi, math.pi),
    ))
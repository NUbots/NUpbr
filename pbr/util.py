import os
import re
import bpy
import bpy_extras
import random as rand
import numpy as np
import math
import cv2
import colorsys

from config import scene_config
from scene import environment as env
from mathutils import Vector

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
                    < scene_config.robot_radius**2
                    for p in ground_points
                ]
            ):
                continue

            ground_points.append(project_to_ground(y, x, cam_location, img, env_info))

    return ground_points


def generate_moves(field_meta, z_coord=0.3):
    """
    Generates world coordinates for all of the robots in world space
    Arguments:
        field_meta (dict): The field meta data - this is where the field dimensions are derived from
        z_coord (float): The z coordinate of the base hip (if the robot mesh is NUgus_esh, and torso if it is just NUgus) from z=0.0
    Returns:
        world_points (list): A list of world coordinates for each robot

    Note: This function also relies from a config value in scene_config.py called robot_radius.
          This radius defines the area around a robot that is considered to be occupied.
          It can also be interpreted as the minimum distance between any two robots.
          This is to make sure that no two robots can look like they have spawned on top of one another.
    """
    field_dims = (
        field_meta["length"] + 2 * field_meta["border_width"],
        field_meta["width"] + 2 * field_meta["border_width"],
    )

    # Use the field dimensions to generate a set of moves for the robots
    abs_x, abs_y = field_dims

    world_points = []

    while len(world_points) < scene_config.num_robots + scene_config.num_misc_robots:
        # Get random field point
        point = np.random.uniform(
            low=(-abs_x / 2, -abs_y / 2), high=(abs_x / 2, abs_y / 2)
        )
        # If any of the points are within the radius of a robot, skip this point
        if any(
            [
                (p[0] - point[0]) ** 2 + (p[1] - point[1]) ** 2
                < scene_config.robot_radius**2
                for p in world_points
            ]
        ):
            continue

        # Add the point to the list if the current iteration is not skipped
        world_points.append((*point, z_coord))

    return world_points

# Find the forward vector of an object that you pass in
def find_forward_vector(obj):
    local_matrix = obj.matrix_local
    global_matrix = obj.matrix_world @ local_matrix
    rotation_matrix = global_matrix.to_3x3()
    forward = rotation_matrix @ Vector((1, 0, 0))
    forward.z = 0  # Set the Z component of the forward vector to 0 to make it parallel to the ground
    forward.normalize()  # Normalize the forward vector after setting Z to 0

    return forward

def random_jersey_colour():
    """Generates a random, vividly-coloured jersey colour.

    Returns a tuple of ((r, g, b) floats in [0, 1], "#rrggbb" hex string).
    """
    r, g, b = colorsys.hsv_to_rgb(rand.random(), rand.uniform(0.6, 1.0), rand.uniform(0.6, 1.0))
    hex_colour = "#{:02x}{:02x}{:02x}".format(round(r * 255), round(g * 255), round(b * 255))
    return (r, g, b), hex_colour


def _is_robot_part(name):
    """Returns True if an object name matches the "r<number>_<part>" robot naming scheme"""
    prefix = name.split("_")[0]
    return prefix.startswith("r") and prefix[1:].isdigit()


def _is_occluded(scene, cam, world_point, exclude_prefix=None, exclude_obj=None):
    """Returns True if the line of sight from the camera to world_point is blocked by
    something other than the target itself (or, for robots, one of its own parts, since
    self-occlusion by a robot's own limb is not real occlusion for annotation purposes)."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    cam_pos = cam.matrix_world.translation
    to_point = world_point - cam_pos
    distance = to_point.length

    if distance < 1e-6:
        return False

    # Start the ray a bit along the path so it doesn't immediately self-hit the camera-mounting
    # robot's own head, then only travel as far as the target (plus a small margin). A fixed
    # travel distance would wrongly mark distant-but-unobstructed objects as occluded.
    origin = cam_pos + to_point * 0.2
    remaining_distance = distance * 0.85

    hit, _loc, _normal, _idx, hit_obj, _matrix = scene.ray_cast(
        depsgraph, origin, to_point.normalized(), distance=remaining_distance
    )

    if not hit:
        return False
    if exclude_obj is not None and hit_obj == exclude_obj:
        return False
    if exclude_prefix is not None and hit_obj is not None and hit_obj.name.startswith(exclude_prefix):
        return False

    return True


def get_robot_bounding_box(robot_obj, cam, scene):
    """Calculates a 2D bounding box for a robot from all of its parts (rectilinear camera)"""
    robot_prefix = robot_obj.name.split("_")[0]
    robot_parts = [o for o in bpy.data.objects if o.name.startswith(robot_prefix + "_")]

    # Gate on the robot's root part first: if it isn't cleanly in view (in front of the
    # camera, inside the frame, not blocked by something else) don't annotate the robot at
    # all. Without this, a single limb poking into frame at a weird angle can otherwise
    # produce a "bounding box" spanning almost the entire image.
    root_world = robot_obj.matrix_world.translation
    root_view = bpy_extras.object_utils.world_to_camera_view(scene, cam, root_world)
    if root_view.z <= 0 or not (0.0 <= root_view.x <= 1.0 and 0.0 <= root_view.y <= 1.0):
        return None

    if _is_occluded(scene, cam, root_world, exclude_prefix=robot_prefix):
        return None

    screen_positions = []
    for part in robot_parts:
        for corner in part.bound_box:
            cam_view = bpy_extras.object_utils.world_to_camera_view(
                scene, cam, part.matrix_world @ Vector(corner)
            )
            if cam_view.z > 0:  # Only use points in front of the camera
                screen_positions.append(cam_view)

    if not screen_positions:
        return None

    min_x = min(p.x for p in screen_positions) * scene.render.resolution_x
    max_x = max(p.x for p in screen_positions) * scene.render.resolution_x
    min_y = min(p.y for p in screen_positions) * scene.render.resolution_y
    max_y = max(p.y for p in screen_positions) * scene.render.resolution_y

    return (min_x, min_y, max_x, max_y)


def get_robot_bounding_box_panoramic(obj, h, w, lens, fov, cam, scene):
    """Calculates a 2D bounding box for a robot from all of its parts (equisolid fisheye camera)"""
    robot_prefix = obj.name.split("_")[0]
    robot_parts = [o for o in bpy.data.objects if o.name.startswith(robot_prefix + "_")]

    cam_inv = cam.matrix_world.inverted()
    root_world = obj.matrix_world.translation
    root_cam = cam_inv @ root_world

    # In camera-local space, forward is -Z, so z < 0 means "in front of the camera". For a
    # unit vector this also guarantees theta (angle from the optical axis) <= 90 degrees.
    if root_cam.z >= 0:
        return None

    root_l = min(math.sqrt(root_cam.x**2 + root_cam.y**2), 0.999)
    if math.asin(root_l) > fov / 2.0:
        return None

    if _is_occluded(scene, cam, root_world, exclude_prefix=robot_prefix):
        return None

    screen_positions = []
    for part in robot_parts:
        for corner in part.bound_box:
            bbox_corner = cam_inv @ (part.matrix_world @ Vector(corner))

            # Skip corners behind the camera (or outside the fisheye FOV): folding them into
            # the front hemisphere via asin/atan2 would place them at a bogus screen location,
            # which is what causes a single out-of-view limb to blow the bbox out to the edges
            # of the image.
            if bbox_corner.z >= 0:
                continue

            l = min(math.sqrt(bbox_corner.x**2 + bbox_corner.y**2), 0.999)
            theta = math.asin(l)
            if theta > fov / 2.0:
                continue

            phi = math.atan2(bbox_corner.y, bbox_corner.x)

            # Equisolid projection
            r = 2.0 * lens * math.sin(theta / 2)

            u = r * math.cos(phi) / w + 0.5
            v = r * math.sin(phi) / h + 0.5

            screen_positions.append(
                Vector((u * scene.render.resolution_x, v * scene.render.resolution_y))
            )

    if not screen_positions:
        return None

    min_x = min(p.x for p in screen_positions)
    max_x = max(p.x for p in screen_positions)
    min_y = min(p.y for p in screen_positions)
    max_y = max(p.y for p in screen_positions)

    return (min_x, min_y, max_x, max_y)


def get_bounding_box(obj):
    """Calculates 2D bounding box for YOLO format (rectilinear camera)"""
    cam = bpy.context.scene.camera
    scene = bpy.context.scene

    # Special handling for ball objects (spheres)
    if obj.name == "Ball":
        return get_sphere_bounding_box(obj, cam, scene)

    # Special handling for robot objects - robot parts follow the pattern
    # "r<number>_<part>" (e.g., "r6_Torso")
    if _is_robot_part(obj.name):
        return get_robot_bounding_box(obj, cam, scene)

    # Default bounding box calculation for other objects
    bbox_corners = [
        bpy_extras.object_utils.world_to_camera_view(scene, cam, obj.matrix_world @ Vector(corner))
        for corner in obj.bound_box
    ]

    # Check if any corners are behind the camera
    valid_corners = [corner for corner in bbox_corners if corner.z > 0]
    if not valid_corners:
        return None

    min_x = min(corner.x for corner in valid_corners) * scene.render.resolution_x
    max_x = max(corner.x for corner in valid_corners) * scene.render.resolution_x
    min_y = min(corner.y for corner in valid_corners) * scene.render.resolution_y
    max_y = max(corner.y for corner in valid_corners) * scene.render.resolution_y

    return (min_x, min_y, max_x, max_y)


def get_bounding_box_panoramic(obj):
    """Calculates 2D bounding box for YOLO format (equisolid fisheye camera)"""
    cam = bpy.context.scene.camera
    scene = bpy.context.scene

    lens = cam.data.cycles.fisheye_lens
    fov = cam.data.cycles.fisheye_fov

    aspect_ratio = scene.render.resolution_x / scene.render.resolution_y
    if cam.data.sensor_fit == "VERTICAL":
        h = cam.data.sensor_height
        w = aspect_ratio * h
    else:
        w = cam.data.sensor_width
        h = w / aspect_ratio

    # Special handling for ball objects (spheres)
    if obj.name == "Ball":
        return get_sphere_bounding_box_panoramic(obj, h, w, lens, fov, cam, scene)

    # Special handling for robot objects - robot parts follow the pattern
    # "r<number>_<part>" (e.g., "r6_Torso")
    if _is_robot_part(obj.name):
        return get_robot_bounding_box_panoramic(obj, h, w, lens, fov, cam, scene)

    # Generic fallback for any other object type (e.g. goals, shapes)
    cam_inv = cam.matrix_world.inverted()
    screen_positions = []

    for corner in obj.bound_box:
        bbox_corner = cam_inv @ (obj.matrix_world @ Vector(corner))

        if bbox_corner.z >= 0:
            continue

        l = min(math.sqrt(bbox_corner.x**2 + bbox_corner.y**2), 0.999)
        theta = math.asin(l)
        if theta > fov / 2.0:
            continue

        phi = math.atan2(bbox_corner.y, bbox_corner.x)

        # Equisolid projection
        r = 2.0 * lens * math.sin(theta / 2)

        u = r * math.cos(phi) / w + 0.5
        v = r * math.sin(phi) / h + 0.5

        screen_positions.append(Vector((u * scene.render.resolution_x, v * scene.render.resolution_y)))

    if not screen_positions:
        return None

    min_x = min(p.x for p in screen_positions)
    max_x = max(p.x for p in screen_positions)
    min_y = min(p.y for p in screen_positions)
    max_y = max(p.y for p in screen_positions)

    return (min_x, min_y, max_x, max_y)


def get_sphere_bounding_box(obj, cam, scene):
    """Calculates a 2D bounding box for the (roughly spherical) ball, using a rectilinear camera"""
    world_center = obj.matrix_world.translation
    center_2d = bpy_extras.object_utils.world_to_camera_view(scene, cam, world_center)

    # Reject if the ball's centre isn't cleanly in front of and inside the camera frame
    if center_2d.z <= 0 or not (0.0 <= center_2d.x <= 1.0 and 0.0 <= center_2d.y <= 1.0):
        return None

    if _is_occluded(scene, cam, world_center, exclude_obj=obj):
        return None

    radius = max(obj.dimensions) / 2.0

    camera_pos = cam.matrix_world.translation
    distance = (world_center - camera_pos).length

    center_x_pixels = center_2d.x * scene.render.resolution_x
    center_y_pixels = center_2d.y * scene.render.resolution_y

    # Apparent size in pixels from the camera focal length
    focal_length = cam.data.lens  # in mm
    sensor_width = cam.data.sensor_width  # in mm
    apparent_diameter = (radius * 2.0 / distance) * focal_length * (scene.render.resolution_x / sensor_width)
    radius_pixels = apparent_diameter / 2.0

    min_x = center_x_pixels - radius_pixels
    max_x = center_x_pixels + radius_pixels
    min_y = center_y_pixels - radius_pixels
    max_y = center_y_pixels + radius_pixels

    return (min_x, min_y, max_x, max_y)


def get_sphere_bounding_box_panoramic(obj, h, w, lens, fov, cam, scene):
    """Calculates a 2D bounding box for the ball using an equisolid fisheye camera"""
    world_center = obj.matrix_world.translation
    cam_inv = cam.matrix_world.inverted()
    center = cam_inv @ world_center

    if center.z >= 0:  # Behind the camera
        return None

    l = min(math.sqrt(center.x**2 + center.y**2), 0.999)
    theta = math.asin(l)
    if theta > fov / 2.0:  # Outside the fisheye field of view
        return None

    if _is_occluded(scene, cam, world_center, exclude_obj=obj):
        return None

    radius = max(obj.dimensions) / 2.0
    camera_pos = cam.matrix_world.translation
    distance = (world_center - camera_pos).length

    apparent_diameter = (radius * 2.0 / distance) * lens * (scene.render.resolution_x / w)
    radius_pixels = apparent_diameter / 2.0

    phi = math.atan2(center.y, center.x)

    # Equisolid projection
    r = 2.0 * lens * math.sin(theta / 2)

    u = r * math.cos(phi) / w + 0.5
    v = r * math.sin(phi) / h + 0.5

    x = u * scene.render.resolution_x
    y = v * scene.render.resolution_y

    return (x - radius_pixels, y - radius_pixels, x + radius_pixels, y + radius_pixels)


def write_annotations(obj):
    """Returns the bounding box for obj as integer pixel coordinates
    (x_min, y_min, x_max, y_max), using the standard image convention (origin top-left,
    y increasing downward) - or None if the object isn't visible / doesn't pass the
    annotation gate."""
    scene = bpy.context.scene
    cam = bpy.context.scene.camera

    # Never annotate objects that aren't actually being rendered this frame
    if obj.hide_render:
        return None

    if cam.data.type == "PERSP":
        bbox_result = get_bounding_box(obj)
    else:
        bbox_result = get_bounding_box_panoramic(obj)

    if bbox_result is None:
        return None

    min_x, min_y, max_x, max_y = bbox_result

    # Clamp bounding box to image bounds (still in the bottom-left-origin coordinate system
    # used internally by the projection helpers above)
    min_x = max(0, min_x)
    min_y = max(0, min_y)
    max_x = min(scene.render.resolution_x, max_x)
    max_y = min(scene.render.resolution_y, max_y)

    if min_x >= max_x or min_y >= max_y:
        return None

    width_px = max_x - min_x
    height_px = max_y - min_y

    min_size_pixels = scene_config.resources["bounding_boxes"]["min_bbox_size"]
    max_size_pixels = scene_config.resources["bounding_boxes"]["max_bbox_size"]

    if width_px < min_size_pixels or height_px < min_size_pixels:
        return None

    # A bbox this large is not a real detection - it's almost always the leftover artefact of
    # a barely-in-frame object (e.g. one limb of a robot standing just behind the camera)
    if width_px > max_size_pixels or height_px > max_size_pixels:
        print(
            f"[WARN] Discarding implausibly large bounding box for {obj.name}: "
            f"{width_px:.0f}x{height_px:.0f}px"
        )
        return None

    # Flip Y to the standard top-left-origin image coordinate convention
    y_min_img = scene.render.resolution_y - max_y
    y_max_img = scene.render.resolution_y - min_y

    return (round(min_x), round(y_min_img), round(max_x), round(y_max_img))


def _robot_partially_visible(obj):
    """Cheap, conservative check for whether any part of a robot projects into the visible
    frame, in front of the camera (ignoring occlusion and exact framing). Used to catch
    robots that would show up on screen but get rejected by write_annotations' stricter
    gate, so the caller can re-roll the scene rather than render an unlabelled robot."""
    cam = bpy.context.scene.camera
    scene = bpy.context.scene
    robot_prefix = obj.name.split("_")[0]
    robot_parts = [o for o in bpy.data.objects if o.name.startswith(robot_prefix + "_")]

    if cam.data.type == "PERSP":
        for part in robot_parts:
            view = bpy_extras.object_utils.world_to_camera_view(
                scene, cam, part.matrix_world.translation
            )
            if view.z > 0 and 0.0 <= view.x <= 1.0 and 0.0 <= view.y <= 1.0:
                return True
        return False

    lens = cam.data.cycles.fisheye_lens
    fov = cam.data.cycles.fisheye_fov
    cam_inv = cam.matrix_world.inverted()
    for part in robot_parts:
        local = cam_inv @ part.matrix_world.translation
        if local.z >= 0:
            continue
        l = min(math.sqrt(local.x**2 + local.y**2), 0.999)
        if math.asin(l) <= fov / 2.0:
            return True
    return False


def _ball_partially_visible(obj):
    """Cheap, conservative check for whether the ball might be poking into the visible
    frame. Uses a small margin around the strict frame boundary since the ball has real
    size - its edge can be on screen even when its centre isn't quite."""
    cam = bpy.context.scene.camera
    scene = bpy.context.scene
    world_center = obj.matrix_world.translation

    if cam.data.type == "PERSP":
        view = bpy_extras.object_utils.world_to_camera_view(scene, cam, world_center)
        margin = 0.05
        return view.z > 0 and -margin <= view.x <= 1 + margin and -margin <= view.y <= 1 + margin

    fov = cam.data.cycles.fisheye_fov
    cam_inv = cam.matrix_world.inverted()
    local = cam_inv @ world_center
    if local.z >= 0:
        return False
    l = min(math.sqrt(local.x**2 + local.y**2), 0.999)
    return math.asin(l) <= fov / 2.0 + math.radians(3)


def is_visible_but_unannotated(obj, is_robot):
    """Returns True if obj would plausibly show up on screen but write_annotations would
    reject it - i.e. rendering this frame as-is would produce an unlabelled visible
    object. Only meaningful to call once the scene/camera for this frame has been fully
    updated (positions set, view_layer updated)."""
    if obj.hide_render:
        return False

    partially_visible = _robot_partially_visible(obj) if is_robot else _ball_partially_visible(obj)
    if not partially_visible:
        return False

    return write_annotations(obj) is None


def write_goal_post_annotations_from_mask(mask_path, scene):
    """Generate goal post annotations from segmentation mask"""
    import cv2
    import numpy as np
    
    try:
        mask_img = cv2.imread(mask_path)
    except:
        print(f"Cannot load mask image {mask_path}")
        return []
    
    if mask_img is None:
        print(f"Failed to read mask image {mask_path}")
        return []
    
    annotations = []
    
    # Goal posts should be yellow in the segmentation mask
    # Convert BGR to RGB and look for yellow pixels
    mask_rgb = cv2.cvtColor(mask_img, cv2.COLOR_BGR2RGB)
    
    # Define yellow color range (goal posts)
    # Yellow in RGB is approximately (255, 255, 0)
    yellow_lower = np.array([250, 250, 0])
    yellow_upper = np.array([255, 255, 10])
    
    # Create mask for yellow pixels (goal posts)
    yellow_mask = cv2.inRange(mask_rgb, yellow_lower, yellow_upper)
    
    # Find contours in the yellow mask
    contours, _ = cv2.findContours(yellow_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    goalpost_class_id = 1  # Goal posts have class 1
    
    for contour in contours:
        # Calculate bounding box for each goal post contour
        x, y, w, h = cv2.boundingRect(contour)
        
        # Check minimum size requirements
        min_size_pixels = scene_config.resources["bounding_boxes"]["min_bbox_size"]
        if w < min_size_pixels or h < min_size_pixels:
            print(f"Goal post contour too small: {w}x{h}")
            continue
        
        # Convert to YOLO format (normalized center coordinates and dimensions)
        img_height, img_width = mask_img.shape[:2]
        
        center_x = (x + w/2) / img_width
        center_y = (y + h/2) / img_height
        width_norm = w / img_width
        height_norm = h / img_height
        
        # Ensure coordinates are within bounds
        if 0 <= center_x <= 1 and 0 <= center_y <= 1:
            print(f"Goal post from mask: {goalpost_class_id} {center_x:.6f} {center_y:.6f} {width_norm:.6f} {height_norm:.6f}")
            annotations.append((goalpost_class_id, center_x, center_y, width_norm, height_norm))
    
    print(f"Generated {len(annotations)} goal post annotations from mask")
    return annotations

def write_intersection_annotations_from_mask(mask_path, scene):
    """Generate intersection annotations from segmentation mask"""
    import cv2
    import numpy as np
    
    try:
        mask_img = cv2.imread(mask_path)
    except:
        print(f"Cannot load mask image {mask_path}")
        return []
    
    if mask_img is None:
        print(f"Failed to read mask image {mask_path}")
        return []
    
    annotations = []
    
    # Convert BGR to RGB for color detection
    mask_rgb = cv2.cvtColor(mask_img, cv2.COLOR_BGR2RGB)
    
    # Define color ranges and class IDs for different intersection types
    intersection_types = {
        "L": {
            "class_id": 3,
            "color_lower": np.array([250, 0, 250]),    # Magenta lower bound
            "color_upper": np.array([255, 10, 255])   # Magenta upper bound
        },
        "T": {
            "class_id": 4,
            "color_lower": np.array([0, 250, 250]),    # Cyan lower bound
            "color_upper": np.array([10, 255, 255])   # Cyan upper bound
        },
        "X": {
            "class_id": 5,
            "color_lower": np.array([250, 90, 0]),    # Orange lower bound
            "color_upper": np.array([255, 110, 0])    # Orange upper bound
        }
    }
    
    for intersection_type, config in intersection_types.items():
        # Create mask for this intersection type's color
        color_mask = cv2.inRange(mask_rgb, config["color_lower"], config["color_upper"])
        
        # Find contours in the color mask
        contours, _ = cv2.findContours(color_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            # Calculate bounding box for each intersection contour
            x, y, w, h = cv2.boundingRect(contour)
            
            # Check minimum size requirements
            min_size_pixels = scene_config.resources["bounding_boxes"]["min_bbox_size"]
            if w < min_size_pixels or h < min_size_pixels:
                print(f"{intersection_type}-intersection contour too small: {w}x{h}")
                continue
            
            # Convert to YOLO format (normalized center coordinates and dimensions)
            img_height, img_width = mask_img.shape[:2]
            
            center_x = (x + w/2) / img_width
            center_y = (y + h/2) / img_height
            width_norm = w / img_width
            height_norm = h / img_height
            
            # Ensure coordinates are within bounds
            if 0 <= center_x <= 1 and 0 <= center_y <= 1:
                print(f"{intersection_type}-intersection from mask: {config['class_id']} {center_x:.6f} {center_y:.6f} {width_norm:.6f} {height_norm:.6f}")
                annotations.append((config["class_id"], center_x, center_y, width_norm, height_norm))
    
    print(f"Generated {len(annotations)} intersection annotations from mask")
    return annotations

import os
import re
import bpy
import random as rand
import numpy as np
import math
import cv2

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

def get_robot_bounding_box(robot_obj, cam, scene):
    """Calculates 2D bounding box for robot objects with all their parts"""
    import bpy_extras
    
    # Extract robot number from the object name (e.g., "r6_Torso" -> "r6")
    robot_prefix = robot_obj.name.split('_')[0]  # e.g., "r6"
    
    # Find all objects that belong to this robot
    robot_parts = []
    for obj in bpy.data.objects:
        if obj.name.startswith(robot_prefix + '_'):
            robot_parts.append(obj)
    
    print(f"Found {len(robot_parts)} parts for robot {robot_prefix}")
    
    # Collect all bounding box corners from all robot parts
    all_corners = []
    
    for part in robot_parts:
        # Get the 8 corners of each part's bounding box in world coordinates
        for corner in part.bound_box:
            world_corner = part.matrix_world @ Vector(corner)
            # Project to camera view
            camera_corner = bpy_extras.object_utils.world_to_camera_view(scene, cam, world_corner)
            if camera_corner.z > 0:  # Only use points in front of camera
                all_corners.append(camera_corner)
    
    if not all_corners:
        print(f"No valid corners found for robot {robot_prefix}")
        return None
    
    # Find the overall min/max bounds
    min_x = min(corner.x for corner in all_corners)
    max_x = max(corner.x for corner in all_corners)
    min_y = min(corner.y for corner in all_corners)
    max_y = max(corner.y for corner in all_corners)
    
    # Convert to pixels
    min_x *= scene.render.resolution_x
    max_x *= scene.render.resolution_x
    min_y *= scene.render.resolution_y
    max_y *= scene.render.resolution_y
    
    print(f"Robot {robot_prefix} combined bbox: ({min_x:.1f}, {min_y:.1f}, {max_x:.1f}, {max_y:.1f})")
    return (min_x, min_y, max_x, max_y)

def get_bounding_box(obj):
    """Calculates 2D bounding box for YOLO format"""
    import bpy_extras
    cam = bpy.context.scene.camera
    scene = bpy.context.scene

    # Special handling for ball objects (spheres)
    if obj.name == "Ball":
        return get_sphere_bounding_box(obj, cam, scene)
    
    # Special handling for robot objects - check if this looks like a robot part
    # Robot parts follow pattern "r<number>_<part>" (e.g., "r6_Torso")
    if '_' in obj.name and obj.name.split('_')[0].startswith('r') and obj.name.split('_')[0][1:].isdigit():
        return get_robot_bounding_box(obj, cam, scene)
    
    # Default bounding box calculation for other objects
    bbox_corners = [bpy_extras.object_utils.world_to_camera_view(scene, cam, obj.matrix_world @ Vector(corner)) for corner in obj.bound_box]

    # Check if any corners are behind the camera
    valid_corners = [corner for corner in bbox_corners if corner.z > 0]
    if not valid_corners:
        print(f"All corners of {obj.name} are behind camera")
        return None

    min_x = min(corner.x for corner in valid_corners)
    max_x = max(corner.x for corner in valid_corners)
    min_y = min(corner.y for corner in valid_corners)
    max_y = max(corner.y for corner in valid_corners)

    # Convert to pixels
    min_x *= scene.render.resolution_x
    max_x *= scene.render.resolution_x
    min_y *= scene.render.resolution_y
    max_y *= scene.render.resolution_y
    
    print(f"{obj.name} bbox: ({min_x:.1f}, {min_y:.1f}, {max_x:.1f}, {max_y:.1f})")
    return (min_x, min_y, max_x, max_y)

def get_sphere_bounding_box(obj, cam, scene):
    """Calculates accurate 2D bounding box for spherical objects"""
    import bpy_extras
    
    # Check camera type - equisolid cameras need different handling
    camera_type = getattr(cam.data, 'type', 'PERSP')
    
    # Get the sphere center in world coordinates
    world_center = obj.matrix_world.translation
    radius = max(obj.dimensions) / 2.0
    
    # For now, disable equisolid handling and use perspective projection for all cameras
    # This ensures consistent, reliable bounding boxes
    # TODO: Re-enable equisolid handling once perspective projection is perfected
    
    # Regular perspective camera handling for all camera types
    # Project sphere center to camera view
    center_2d = bpy_extras.object_utils.world_to_camera_view(scene, cam, world_center)
    
    # Check if sphere center is behind camera
    if center_2d.z <= 0:
        print(f"Ball behind camera, z={center_2d.z}")
        return None
    
    # Convert to pixel coordinates (same system as regular bbox function)
    center_x_pixels = center_2d.x * scene.render.resolution_x
    center_y_pixels = center_2d.y * scene.render.resolution_y
    
    # Calculate distance from camera to ball
    camera_pos = cam.matrix_world.translation
    distance = (world_center - camera_pos).length
    
    # Simple perspective projection for radius
    # Use camera focal length to calculate apparent size
    focal_length = cam.data.lens  # in mm
    sensor_width = cam.data.sensor_width  # in mm
    
    # Calculate apparent size in pixels
    # apparent_size = (object_size / distance) * focal_length * (image_width / sensor_width)
    apparent_diameter = (radius * 2.0 / distance) * focal_length * (scene.render.resolution_x / sensor_width)
    radius_pixels = apparent_diameter / 2.0
    
    # Calculate bounding box
    min_x = center_x_pixels - radius_pixels
    max_x = center_x_pixels + radius_pixels
    min_y = center_y_pixels - radius_pixels
    max_y = center_y_pixels + radius_pixels
    
    print(f"Ball bbox: center=({center_2d.x:.3f}, {center_2d.y:.3f}), radius={radius:.3f}")
    print(f"Ball bbox: distance={distance:.1f}m, apparent_diameter={apparent_diameter:.1f}px")
    print(f"Ball bbox: center_pixels=({center_x_pixels:.1f}, {center_y_pixels:.1f}), radius_pixels={radius_pixels:.1f}")
    print(f"Ball bbox pixels: ({min_x:.1f}, {min_y:.1f}, {max_x:.1f}, {max_y:.1f})")
    
    return (min_x, min_y, max_x, max_y)

def write_annotations(obj, class_id=0):
    """Writes YOLO annotations for the object"""
    scene = bpy.context.scene
    bbox_result = get_bounding_box(obj)
    
    # Check if bounding box calculation failed
    if bbox_result is None:
        print(f"Failed to calculate bounding box for {obj.name}")
        return None
        
    min_x, min_y, max_x, max_y = bbox_result
    
    # Clamp bounding box to image bounds
    min_x = max(0, min_x)
    min_y = max(0, min_y)
    max_x = min(scene.render.resolution_x, max_x)
    max_y = min(scene.render.resolution_y, max_y)
    
    # Check if there's any visible area after clamping
    if min_x >= max_x or min_y >= max_y:
        print(f"No visible area for {obj.name} after clamping")
        return None
    
    # Calculate center and dimensions
    x_center = (min_x + max_x) / 2
    # Use consistent Y-flip for all objects
    y_center = scene.render.resolution_y - (min_y + max_y) / 2
    
    width = max_x - min_x
    height = max_y - min_y

    # Normalize coordinates
    x_center /= scene.render.resolution_x
    y_center /= scene.render.resolution_y
    width /= scene.render.resolution_x
    height /= scene.render.resolution_y

    # Final bounds check on normalized coordinates
    if x_center < 0 or x_center > 1 or y_center < 0 or y_center > 1:
        print(f"Center out of bounds for {obj.name}: ({x_center:.3f}, {y_center:.3f})")
        return None
        
    # Check minimum size requirements
    min_size_pixels = scene_config.resources["bounding_boxes"]["min_bbox_size"]
    if (width * scene.render.resolution_x < min_size_pixels or 
        height * scene.render.resolution_y < min_size_pixels):
        print(f"Bounding box too small for {obj.name}: {width * scene.render.resolution_x:.1f} x {height * scene.render.resolution_y:.1f}")
        return None

    print(f"{obj.name} {class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}")
    return class_id, x_center, y_center, width, height

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

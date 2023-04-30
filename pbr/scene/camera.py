#!/usr/local/blender -P

import os
import bpy
import numpy as np
import mathutils
from mathutils import Vector
import math
from scene.blender_object import BlenderObject
import pdb
import util


class Camera(BlenderObject):
    def __init__(self, name):

        bpy.ops.object.camera_add()

        self.cam = bpy.data.cameras["Camera"]
        self.obj = bpy.data.objects[self.cam.name]
        self.obj.name = name

    # Sets target for camera to track
    def set_tracking_target(self, target):
        # create a tracking target at the location of the ball
        if ("Tracking_Target" not in bpy.data.objects):
            bpy.ops.object.add(type='EMPTY', location=(0, 0, 0))
            bpy.context.active_object.name='Tracking_Target'

        tracking_target = bpy.data.objects["Tracking_Target"]
        tracking_target.location = bpy.data.objects["Ball"].location

        if (not self.ball_in_front(target)):
             print("found one!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            self.move_tracking_target(tracking_target)

        bpy.context.view_layer.objects.active = self.obj
        # tracks the empty's position while keeping camera upright
        if "Track To" not in self.obj.constraints:
            bpy.ops.object.constraint_add(type="TRACK_TO")

        constr = self.obj.constraints["Track To"]
        constr.target = tracking_target
        constr.track_axis = "TRACK_NEGATIVE_Z"
        constr.up_axis = "UP_Y"
        constr.influence = 0.9

    # Add parent camera for stereo vision
    def set_stereo_pair(self, cam):
        # Ensure object is selected to receive added constraints
        bpy.context.view_layer.objects.active = self.obj

        self.obj.parent = cam

        if "Copy Rotation" not in self.obj.constraints:
            bpy.ops.object.constraint_add(type="COPY_ROTATION")

        rot_copy_constr = self.obj.constraints["Copy Rotation"]
        rot_copy_constr.target = cam

        bpy.ops.object.constraint_add(type="CHILD_OF")

        child_constr = self.obj.constraints["Child Of"]
        child_constr.name = "cam_child"
        child_constr.target = cam
        child_constr.use_rotation_x = False
        child_constr.use_rotation_y = False
        child_constr.use_rotation_z = False
        child_constr.use_location_x = False
        child_constr.use_location_y = False
        child_constr.use_location_z = False

    # There is some behaviour that is not working correctly with the child of constraint, I have to investigate further
    def set_robot(self, robot):
        # Ensure object is selected to receive added constraints
        bpy.context.view_layer.objects.active = self.obj

        bpy.ops.object.constraint_add(type="COPY_LOCATION")
        loc_constr = self.obj.constraints["Copy Location"]
        loc_constr.name = "robot_L_Eye_Loc"

        # Bind to robot's chosen eye position - must make sure that the main robot being used is the NUgus_esh
        loc_constr.target = bpy.data.objects[f"{robot.name[:2]}_L_Eye_Socket"]
        self.obj.rotation_euler = [np.pi / 2, 0, np.pi / 2]

    def update(self, cam_config, targets=None):
        # Fix for blender being stupid
        for k in bpy.data.cameras.keys():
            cam = bpy.data.cameras[k]
            if cam_config["type"] == "EQUISOLID":
                cam.type = "PANO"
                cam.cycles.panorama_type = "FISHEYE_EQUISOLID"
                cam.cycles.fisheye_fov = cam_config["fov"]
                cam.cycles.fisheye_lens = cam_config["focal_length"]
            elif cam_config["type"] == "RECTILINEAR":
                cam.type = "PERSP"
                cam.lens_unit = "FOV"
                cam.angle = cam_config["fov"]

        if targets is not None:
            self.obj.rotation_euler = [np.pi / 2, 0, np.pi / 2]
            self.set_tracking_target(target=targets["target"])

    def ball_in_front(self, target):
        # Using head of robot to avoid strange camera vectors
        robot = bpy.context.scene.objects["r0_Head"]

        forward = util.find_forward_vector(robot)

        object_vector = target.location - (robot.location + (forward * 0.4))
        object_vector.z = 0  # Set the Z component of the object vector to 0 to consider only X and Y components
        object_vector.normalize()  # Normalize the object vector after setting Z to 0

        angle = math.degrees(forward.angle(object_vector))

        return (angle < 90)

    # Make sure the tracking target is in front of the robot
    def move_tracking_target(self, target):
        # Using head of robot to avoid strange camera vectors
        robot = bpy.context.scene.objects["r0_Head"]
        forward = util.find_forward_vector(robot)

        z_axis = Vector((0, 0, 1))
        # Add a small offset to prevent robot looking straight down
        base_location = robot.location.copy() + (forward * 0.4)

        # Vector perpendicular to the robot
        perp_vector = forward.cross(z_axis).normalized()
        robot_to_ball_vector = target.location - base_location

        # Move the ball to the correct position along the perp_vector
        projection = robot_to_ball_vector.project(perp_vector)
        new_ball_position = base_location + projection
        bpy.data.objects["Tracking_Target"].location = new_ball_position

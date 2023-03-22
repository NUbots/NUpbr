#!/usr/local/blender -P

import os
import bpy
import numpy as np
from scene.blender_object import BlenderObject


class Camera(BlenderObject):
    def __init__(self, name):

        bpy.ops.object.camera_add()

        self.cam = bpy.data.cameras["Camera"]
        self.obj = bpy.data.objects[self.cam.name]
        self.obj.name = name

    # Sets target for camera to track
    def set_tracking_target(self, target):
        bpy.context.view_layer.objects.active = self.obj

        if "Damped Track" not in self.obj.constraints:
            bpy.ops.object.constraint_add(type="DAMPED_TRACK")

        constr = self.obj.constraints["Damped Track"]
        constr.target = target
        constr.track_axis = "TRACK_NEGATIVE_Z"
        constr.influence = 0.75

        if "Limit Rotation" not in self.obj.constraints:
            bpy.ops.object.constraint_add(type="LIMIT_ROTATION")

        constr = self.obj.constraints["Limit Rotation"]
        constr.use_limit_y = True
        constr.min_y = 0
        constr.max_y = 0
        constr.influence = 1

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

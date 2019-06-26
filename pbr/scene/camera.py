#!/usr/local/blender -P

import os
import bpy

from scene.blender_object import BlenderObject

class Camera(BlenderObject):
    def __init__(self, name):

        bpy.ops.object.camera_add()

        self.cam = bpy.data.cameras["Camera"]
        self.obj = bpy.data.objects[self.cam.name]
        self.obj.name = name

    # Sets target for camera to track
    def set_tracking_target(self, target):
        bpy.context.scene.objects.active = self.obj

        if "Damped Track" not in self.obj.constraints:
            bpy.ops.object.constraint_add(type="DAMPED_TRACK")

        constr = self.obj.constraints["Damped Track"]
        constr.target = target
        constr.track_axis = "TRACK_NEGATIVE_Z"
        constr.influence = 0.75

    # Add parent camera for stereo vision
    def set_stereo_pair(self, cam):
        # Ensure object is selected to receive added constraints
        bpy.context.scene.objects.active = self.obj

        # Make main camera the slow parent to use as a location, rotation and scale basis
        self.obj.parent = cam
        self.obj.use_slow_parent = True

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

    def set_robot(self, robot, height_offset):
        # Ensure object is selected to receive added constraints
        bpy.context.scene.objects.active = self.obj

        bpy.ops.object.constraint_add(type="CHILD_OF")
        child_constr = self.obj.constraints["Child Of"]
        child_constr.name = "robot_child"
        child_constr.target = robot
        # Invert child of
        child_constr.inverse_matrix = robot.matrix_world.inverted()
        # Apply height offset to move cam to head
        self.obj.delta_location[2] = height_offset

    def update(self, cam_config):

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

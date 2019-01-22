#!/usr/local/blender -P

import os
import bpy

from config import scene_config as scene_cfg
from config import blend_config as blend_cfg

from scene.blender_object import BlenderObject

class Camera(BlenderObject):
    def __init__(self, name):
        self.loc = (0., 0., 0.)
        self.obj = None
        self.cam = None
        self.name = name
        self.construct()

    # Sets target for camera to track
    def set_tracking_target(self, target):
        bpy.context.scene.objects.active = self.obj

        if 'Track To' not in self.obj.constraints:
            bpy.ops.object.constraint_add(type='TRACK_TO')

        constr = self.obj.constraints['Track To']
        constr.target = target
        constr.track_axis = 'TRACK_NEGATIVE_Z'
        constr.up_axis = 'UP_Y'
        constr.influence = 0.9

    # Add parent camera for stereo vision
    def set_stereo_pair(self, cam):
        # Ensure object is selected to receive added constraints
        bpy.context.scene.objects.active = self.obj

        # Make main camera the slow parent to use as a location, rotation and scale basis
        self.obj.parent = cam
        self.obj.use_slow_parent = True

        if 'Copy Rotation' not in self.obj.constraints:
            bpy.ops.object.constraint_add(type='COPY_ROTATION')

        rot_copy_constr = self.obj.constraints['Copy Rotation']
        rot_copy_constr.target = cam

        if 'Child Of' not in self.obj.constraints:
            bpy.ops.object.constraint_add(type='CHILD_OF')

        child_constr = self.obj.constraints['Child Of']
        child_constr.target = cam
        child_constr.use_rotation_x = False
        child_constr.use_rotation_y = False
        child_constr.use_rotation_z = False

    def construct(self):
        # Add camera
        bpy.ops.object.camera_add()
        cam = bpy.data.cameras['Camera']
        cam.type = scene_cfg.camera['type']
        if scene_cfg.camera['type'] == 'PANO':
            cam.cycles.type = scene_cfg.camera['cycles']['type']
            cam.cycles.fisheye_lens = scene_cfg.camera['focal_length']
            cam.cycles.fisheye_fov = scene_cfg.camera['fov']
        self.cam = cam

        cam_obj = bpy.data.objects[cam.name]
        # cam_obj.type = scene_cfg.camera['type']
        cam_obj.name = self.name
        self.obj = cam_obj

        for cam in bpy.data.cameras.keys():
            if scene_cfg.camera['type'] == 'PANO':
                bpy.data.cameras[cam].type = 'PANO'
                bpy.data.cameras[cam].cycles.type = scene_cfg.camera['cycles']['type']
                bpy.data.cameras[cam].cycles.fisheye_lens = scene_cfg.camera['focal_length']
                bpy.data.cameras[cam].cycles.fisheye_fov = scene_cfg.camera['fov']

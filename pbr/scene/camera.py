#!/usr/local/blender -P

import os
import bpy

from config import scene_config as scene_cfg
from config import blend_config as blend_cfg

class Camera:
    def __init__(self, name):
        self.loc = (0., 0., 0.)
        self.obj = None
        self.cam = None
        self.name = name
        self.construct()

    # Move relative to field origin
    def move(self, loc):
        self.obj.location = loc

    # Move relative to current position
    def offset(self, loc):
        self.obj.location = (
            self.obj.location[0] + loc[0],
            self.obj.location[1] + loc[1],
            self.obj.location[2] + loc[2],
        )

    def rotate(self, rot):
        self.rot = rot
        self.obj.rotation_euler = rot

    def anchor(self, anch):
        if self.obj is not None:
            self.obj.parent = anch

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
        cam_obj.name = self.name
        self.obj = cam_obj
#!/usr/local/blender -P

import bpy

class CameraAnchor:
    def __init__(self):
        self.loc = (0., 0., 0.)
        self.obj = None
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

    def construct(self):
        # Add camera anchor
        bpy.ops.object.empty_add(type='PLAIN_AXES')
        cam_anch = bpy.data.objects['Empty']
        cam_anch.name = 'Camera_Anchor'

        self.obj = cam_anch
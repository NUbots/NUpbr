#!/usr/local/blender -P

import bpy

from scene.blender_object import BlenderObject


class CameraAnchor(BlenderObject):
    def __init__(self):
        self.loc = (0., 0., 0.)
        self.obj = None
        self.construct()

    def construct(self):
        # Add camera anchor
        bpy.ops.object.empty_add(type='PLAIN_AXES')
        cam_anch = bpy.data.objects['Empty']
        cam_anch.name = 'Camera_Anchor'

        self.obj = cam_anch
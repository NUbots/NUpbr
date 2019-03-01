#!/usr/local/blender -P

import bpy

from scene.blender_object import BlenderObject

class ShadowCatcher(BlenderObject):
    def __init__(self):
        bpy.ops.mesh.primitive_plane_add()
        self.obj = bpy.data.objects['Plane']
        self.obj.name = 'SC_Plane'
        self.obj.cycles.is_shadow_catcher = True
        self.obj.cycles.show_transparent = True
        self.obj.scale = (50, 50, 1)
        self.obj.location = (0, 0, -0.0001)

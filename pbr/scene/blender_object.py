# Super-class for Blender object functions
class BlenderObject:
    def __init__(self):
        self.obj = None

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

    # Rotate object by euler angles
    def rotate(self, rot):
        self.obj.rotation_euler = rot
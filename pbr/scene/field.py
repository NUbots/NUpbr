#!/usr/local/blender -P

import os
import bpy

from config import blend_config as blend_cfg
from config import scene_config as scene_cfg

from scene.blender_object import BlenderObject


class Field(BlenderObject):
    def __init__(self, class_index):
        self.obj = None
        self.lower_plane = None
        self.pass_index = class_index

    # Setup field object
    def update(self, grass_info, field_config):
        # Delete the old field if it exists
        if self.obj is not None:
            bpy.ops.object.select_all(action="DESELECT")
            self.obj.select = True
            bpy.ops.object.delete()
        if self.lower_plane is not None:
            bpy.ops.object.select_all(action="DESELECT")
            self.lower_plane.select = True
            bpy.ops.object.delete()

        # Add plane for field
        bpy.ops.mesh.primitive_plane_add()
        lower_plane = bpy.data.objects["Plane"]
        lower_plane.name = "Lower_Plane"
        lower_plane.pass_index = self.pass_index

        # Define location and dimensions of field
        lower_plane.location = (0, 0, 0)
        lower_plane.dimensions = (
            2 * field_config["border_width"] + field_config["length"],
            2 * field_config["border_width"] + field_config["width"],
            0,
        )

        lower_plane.data.materials.append(
            self.create_lower_plane_mat(
                lower_plane, blend_cfg.field["lower_plane"], grass_info
            )
        )

        # Apply UV mapping to grass
        bpy.ops.uv.smart_project()

        self.lower_plane = lower_plane

        # Add plane for field
        bpy.ops.mesh.primitive_plane_add()
        field = bpy.data.objects["Plane"]
        field.name = "Field"
        field.pass_index = self.pass_index

        # Define location and dimensions of field
        field.location = (0, 0, 0)
        field.dimensions = (
            2 * field_config["border_width"] + field_config["length"],
            2 * field_config["border_width"] + field_config["width"],
            0,
        )

        # Add material to field material slots
        field.data.materials.append(
            self.create_field_mat(field, blend_cfg.field["material"])
        )

        # Apply UV mapping to grass
        bpy.ops.uv.smart_project()

        self.obj = field

    # Set visibility of both field and lower plane
    def hide_render(self, toggle):
        self.obj.hide_render = toggle
        self.lower_plane.hide_render = toggle

    # Create material for the lower plane
    def create_lower_plane_mat(self, f_object, p_cfg, grass_info):
        lp_mat = bpy.data.materials.new("Lower_Plane_Mat")
        # Enable use of material nodes
        lp_mat.use_nodes = True

        # Get our node list to construct our material
        node_list = lp_mat.node_tree.nodes

        # Clear node tree of default settings
        for node in node_list:
            node_list.remove(node)

        #                                                                                        |    Principled BSDF
        #                                            |----> Image Texture ->                     | ->  Base color input
        #                                            |       Diffuse map                         |
        # Texture Coordinate                         |       Color output                        |
        #  UV output           -> Mapping        ->  |----> Image Texture -> |    Bump.Normal -> | ->  Normal input
        #  Object: Lower_Plane     Texture           |       Bump map        | ->  Height input
        #                          Scale X: 0.5      |       Color output    | ->  Normal input
        #                          Scale Y: 0.5      |----> Image Texture -> |
        #                                                    Normal map
        #                                                    Colour output

        # Construct node tree
        # Get texture and object coordinates from object
        n_tex_coord = node_list.new("ShaderNodeTexCoord")
        n_tex_coord.object = f_object

        # Create mapping to allow repetition of texture across plane
        n_mapping = node_list.new("ShaderNodeMapping")
        n_mapping.vector_type = "TEXTURE"
        n_mapping.scale = p_cfg["mapping"]["scale"]

        # Create image textures
        n_tex_diffuse = node_list.new("ShaderNodeTexImage")
        n_tex_diffuse.color_space = "COLOR"
        n_tex_diffuse.projection = "FLAT"
        n_tex_diffuse.interpolation = "Linear"
        n_tex_diffuse.extension = "REPEAT"
        n_tex_normal = node_list.new("ShaderNodeTexImage")
        n_tex_normal.color_space = "NONE"
        n_tex_normal.projection = "FLAT"
        n_tex_normal.interpolation = "Linear"
        n_tex_normal.extension = "REPEAT"
        n_tex_bump = node_list.new("ShaderNodeTexImage")
        n_tex_bump.color_space = "NONE"
        n_tex_bump.projection = "FLAT"
        n_tex_bump.interpolation = "Linear"
        n_tex_bump.extension = "REPEAT"
        try:
            img_diffuse = bpy.data.images.load(grass_info["diffuse"])
        except:
            raise NameError("Cannot load image {0}".format(grass_info["diffuse"]))
        try:
            img_normal = bpy.data.images.load(grass_info["normal"])
        except:
            raise NameError("Cannot load image {0}".format(grass_info["normal"]))
        try:
            img_bump = bpy.data.images.load(grass_info["bump"])
        except:
            raise NameError("Cannot load image {0}".format(grass_info["bump"]))
        n_tex_diffuse.image = img_diffuse
        n_tex_normal.image = img_normal
        n_tex_bump.image = img_bump

        # Create bump node to mix bump map and normal map
        n_bump = node_list.new("ShaderNodeBump")

        n_princ = node_list.new("ShaderNodeBsdfPrincipled")
        n_princ.inputs[5].default_value = p_cfg["principled"]["specular"]
        n_princ.inputs[7].default_value = p_cfg["principled"]["roughness"]

        n_output = node_list.new("ShaderNodeOutputMaterial")

        # Link shaders
        tl = lp_mat.node_tree.links
        tl.new(n_tex_coord.outputs["UV"], n_mapping.inputs["Vector"])
        tl.new(n_mapping.outputs["Vector"], n_tex_diffuse.inputs["Vector"])
        tl.new(n_mapping.outputs["Vector"], n_tex_normal.inputs["Vector"])
        tl.new(n_mapping.outputs["Vector"], n_tex_bump.inputs["Vector"])
        tl.new(n_tex_normal.outputs["Color"], n_bump.inputs["Normal"])
        tl.new(n_tex_bump.outputs["Color"], n_bump.inputs["Height"])
        tl.new(n_tex_diffuse.outputs["Color"], n_princ.inputs["Base Color"])
        tl.new(n_bump.outputs["Normal"], n_princ.inputs["Normal"])
        tl.new(n_princ.outputs["BSDF"], n_output.inputs["Surface"])

        return lp_mat

    # Create material for the field
    def create_field_mat(self, f_object, m_cfg):
        f_mat = bpy.data.materials.new("Field_Mat")
        # Enable use of material nodes
        f_mat.use_nodes = True

        # Get our node list to construct our material
        node_list = f_mat.node_tree.nodes

        # Clear node tree of default settings
        for node in node_list:
            node_list.remove(node)

        #
        # Texture Coordinate -> Image Texture -> Principled BSDF   -> Material Output
        #  UV output             Field image      Base color input     Surface input
        #  Object: Field         Color output     BSDF output
        #

        # Construct node tree
        # Get texture and object coordinates from object
        n_tex_coord = node_list.new("ShaderNodeTexCoord")
        n_tex_coord.object = f_object

        # Create texture image of field UV map
        n_field_lines = node_list.new("ShaderNodeTexImage")
        img_path = os.path.join(
            scene_cfg.resources["field"]["uv_path"],
            scene_cfg.resources["field"]["name"] + scene_cfg.resources["field"]["type"],
        )
        try:
            img = bpy.data.images.load(img_path)
        except:
            raise NameError("Cannot load image {0}".format(img_path))
        n_field_lines.image = img

        n_princ = node_list.new("ShaderNodeBsdfPrincipled")
        n_princ.inputs[7].default_value = m_cfg["principled"]["roughness"]

        n_output = node_list.new("ShaderNodeOutputMaterial")

        # Link shaders
        tl = f_mat.node_tree.links
        tl.new(n_tex_coord.outputs["UV"], n_field_lines.inputs["Vector"])
        tl.new(n_field_lines.outputs["Color"], n_princ.inputs["Base Color"])
        tl.new(n_princ.outputs["BSDF"], n_output.inputs["Surface"])

        return f_mat

    # Create noise texture for grass length variation
    def generate_field_noise(self, n_cfg):
        # Add our noise texture
        bpy.ops.texture.new()
        noise_tex = bpy.data.textures.new("Noise", type=n_cfg["type"])
        # Configure noise parameters
        noise_tex.type = n_cfg["type"]
        noise_tex.contrast = n_cfg["contrast"]
        noise_tex.noise_scale = n_cfg["noise_scale"]
        noise_tex.nabla = n_cfg["nabla"]
        return noise_tex

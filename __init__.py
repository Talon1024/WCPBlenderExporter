# -*- coding: utf8 -*-
# Blender WCP IFF mesh import/export script by Kevin Caccamo
# Copyright © 2013-2016 Kevin Caccamo
# E-mail: kevin@ciinet.org
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.
#
# <pep8-80 compliant>

import bpy
import warnings
from . import import_iff
from . import export_iff

# ExportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper, ExportHelper, axis_conversion
from bpy.props import StringProperty, IntProperty, BoolProperty, EnumProperty
from bpy.types import Operator

bl_info = {
    "name": "WCP/SO Mesh File",
    "author": "Kevin Caccamo",
    "description": "Export to a WCP/SO mesh file.",
    "version": (1, 6, 2),
    "blender": (2, 65, 0),
    "location": "File > Export",
    "warning": "",
    "wiki_url": "http://www.ciinet.org/kevin/"
    "bl_wcp_exporter/bl_wcp_export_manual.html",
    "category": "Import-Export"
}


class ImportIFF(Operator, ImportHelper):
    """Import a WCP/WCSO mesh file"""
    # important since its how bpy.ops.import_test.some_data is constructed
    bl_idname = "import_scene.iff"

    bl_label = "Import WCP/SO IFF mesh file"

    # ExportHelper mixin class uses this
    filename_ext = ".iff"

    filter_glob = StringProperty(
        default="*.iff",
        options={'HIDDEN'}
    )

    texname = StringProperty(
        name="Texture name",
        description="Name to use for the materials and textures. Uses model "
        "filename if blank"
    )

    import_all_lods = BoolProperty(
        name="Import all LODs",
        description="Import all LOD meshes as separate models",
        default=False
    )

    use_facetex = BoolProperty(
        name="Use Face Textures",
        description="Use face textures instead of materials for texturing",
        default=False
    )

    read_mats = BoolProperty(
        name="Read MATs",
        description="Attempt to read MAT files (experimental)",
        default=False
    )

    backend_class_name = "IFFImporter"

    def execute(self, context):
        # WIP
        wc_orientation_matrix = axis_conversion("Z", "Y").to_4x4()

        self.import_bsp = False

        importer = getattr(import_iff, self.backend_class_name)(
            self.filepath, self.texname, wc_orientation_matrix,
            self.import_all_lods, self.use_facetex, self.import_bsp,
            self.read_mats
        )

        importer.load()
        with warnings.catch_warnings(record=True) as wlist:
            for warning in wlist:
                self.report({"WARNING"}, warning.message)
        return {"FINISHED"}


class ExportIFF(Operator, ExportHelper):
    """Export to a WCP/WCSO mesh file"""
    # important since its how bpy.ops.import_test.some_data is constructed
    bl_idname = "export_scene.iff"

    bl_label = "Export WCP/SO IFF mesh file"

    # ExportHelper mixin class uses this
    filename_ext = ".iff"

    filter_glob = StringProperty(
        default="*.iff",
        options={'HIDDEN'},
    )

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    texnum = IntProperty(
        name="MAT number",
        description="The number that the MAT texture indices will start at",
        default=22000,
        subtype="UNSIGNED",
        min=0,
        max=99999990
    )

    apply_modifiers = BoolProperty(
        name="Apply Modifiers",
        description="Apply Modifiers to exported model",
        default=True
    )

    active_as_lod0 = BoolProperty(
        name="Active object is LOD0",
        description="Use the active object as the LOD 0 mesh",
        default=True
    )

    # Not implemented as of now
    # generate_bsp = BoolProperty(
    #         name = "Generate BSP",
    #         description = "Generate a BSP tree "
    #         "(for corvette and capship hull/component meshes)",
    #         default = False
    #     )

    axis_forward = EnumProperty(
        name="Forward Axis",
        items=(('X', "X Forward", ""),
               ('Y', "Y Forward", ""),
               ('Z', "Z Forward", ""),
               ('-X', "-X Forward", ""),
               ('-Y', "-Y Forward", ""),
               ('-Z', "-Z Forward", ""),
               ),
        default='Y',
    )

    axis_up = EnumProperty(
        name="Up Axis",
        items=(('X', "X Up", ""),
               ('Y', "Y Up", ""),
               ('Z', "Z Up", ""),
               ('-X', "-X Up", ""),
               ('-Y', "-Y Up", ""),
               ('-Z', "-Z Up", ""),
               ),
        default='Z',
    )

    use_facetex = BoolProperty(
        name="Use Face Textures",
        description="Use face textures instead of materials for texturing",
        default=False
    )

    include_far_chunk = BoolProperty(
        name="Include FAR Chunk",
        description="Include the 'FAR ' CHUNK when exporting to IFF. Only "
        "required if the ship being exported is a fighter.",
        default=True
    )

    # Useless. Other exporters for Blender use separate classes for other
    # formats.
    # output_format = EnumProperty(
    #         name="Output Format",
    #         items=(('Binary', "Binary IFF Format", ""),
    #               ('Source', "IFF Source Code", "")
    #               ),
    #         default='Binary',
    #         )

    backend_class_name = "IFFExporter"

    def execute(self, context):
        # Get the matrix to transform the model to "WCP/SO" orientation
        wc_orientation_matrix = axis_conversion(
            self.axis_forward, self.axis_up, "Z", "Y"
        ).to_4x4()

        # Create the output file if it doesn't already exist
        try:
            outfile = open(self.filepath, "x")
            outfile.close()
        except FileExistsError:
            self.report({"INFO"}, "File already exists!")

        # NOTE: BSP Tree generation is not implemented!
        # As a fallback measure, I'm hard-coding this attribute for now.
        self.generate_bsp = False

        exporter = getattr(export_iff, self.backend_class_name)(
            self.filepath, self.texnum, self.apply_modifiers,
            self.active_as_lod0, self.use_facetex, wc_orientation_matrix,
            self.include_far_chunk, self.generate_bsp
        )

        exporter.export()
        with warnings.catch_warnings(record=True) as wlist:
            for warning in wlist:
                self.report({"WARNING"}, warning.message)
        return {"FINISHED"}


class ExportXMF(Operator, ExportHelper):
    """Export to XMF source code for a WCP/WCSO IFF mesh file"""
    # important since its how bpy.ops.import_test.some_data is constructed
    bl_idname = "export_scene.xmf"

    bl_label = "Export WCP/SO IFF mesh XMF source file"

    # ExportHelper mixin class uses this
    filename_ext = ".pas"

    filter_glob = StringProperty(
        default="*.pas",
        options={'HIDDEN'},
    )

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    texnum = IntProperty(
        name="MAT number",
        description="The number that the MAT texture indices"
        " will start at",
        default=22000,
        subtype="UNSIGNED",
        min=0,
        max=99999990
    )

    apply_modifiers = BoolProperty(
        name="Apply Modifiers",
        description="Apply Modifiers to exported model",
        default=True
    )

    active_as_lod0 = BoolProperty(
        name="Active object is LOD0",
        description="Use the active object as the LOD 0 mesh",
        default=True
    )

    # Not implemented as of now
    # generate_bsp = BoolProperty(
    #         name = "Generate BSP",
    #         description = "Generate a BSP tree "
    #         "(for corvette and capship component meshes)",
    #         default = False
    #     )

    axis_forward = EnumProperty(
        name="Forward Axis",
        items=(('X', "X Forward", ""),
               ('Y', "Y Forward", ""),
               ('Z', "Z Forward", ""),
               ('-X', "-X Forward", ""),
               ('-Y', "-Y Forward", ""),
               ('-Z', "-Z Forward", ""),
               ),
        default='Y',
    )

    axis_up = EnumProperty(
        name="Up Axis",
        items=(('X', "X Up", ""),
               ('Y', "Y Up", ""),
               ('Z', "Z Up", ""),
               ('-X', "-X Up", ""),
               ('-Y', "-Y Up", ""),
               ('-Z', "-Z Up", ""),
               ),
        default='Z',
    )

    use_facetex = BoolProperty(
        name="Use Face Textures",
        description="Use face textures instead of materials for texturing",
        default=False
    )

    backend_class_name = "XMFExporter"

    def execute(self, context):
        # Get the matrix to transform the model to "WCP/SO" orientation
        wc_orientation_matrix = axis_conversion(
            self.axis_forward, self.axis_up, "Z", "Y"
        ).to_4x4()

        # Create the output file if it doesn't already exist
        try:
            outfile = open(self.filepath, "x")
            outfile.close()
        except FileExistsError:
            self.report({"INFO"}, "File already exists!")

        # NOTE: BSP Tree generation is not implemented!
        # As a fallback measure, I'm hard-coding this attribute
        self.generate_bsp = False

        exporter = getattr(export_iff, self.backend_class_name)(
            self.filepath, self.texnum, self.apply_modifiers,
            self.active_as_lod0, self.use_facetex, wc_orientation_matrix,
            self.generate_bsp
        )

        exporter.export()
        with warnings.catch_warnings(record=True) as wlist:
            for warning in wlist:
                self.report({"WARNING"}, warning.message)
        return {"FINISHED"}


# Only needed if you want to add into a dynamic menu
def menu_func_export_iff(self, context):
    self.layout.operator(ExportIFF.bl_idname, text="WCP/SO IFF Mesh (.iff)")


def menu_func_import_iff(self, context):
    self.layout.operator(ImportIFF.bl_idname, text="WCP/SO IFF Mesh (.iff)")


def menu_func_export_xmf(self, context):
    self.layout.operator(ExportXMF.bl_idname,
                         text="WCP/SO IFF Mesh XMF source (.pas)")


def register():
    bpy.utils.register_class(ImportIFF)
    bpy.types.INFO_MT_file_import.append(menu_func_import_iff)
    bpy.utils.register_class(ExportIFF)
    bpy.types.INFO_MT_file_export.append(menu_func_export_iff)
    # bpy.utils.register_class(ExportXMF)
    # bpy.types.INFO_MT_file_export.append(menu_func_export_xmf)


def unregister():
    bpy.utils.unregister_class(ImportIFF)
    bpy.types.INFO_MT_file_import.append(menu_func_import_iff)
    bpy.utils.unregister_class(ExportIFF)
    bpy.types.INFO_MT_file_export.remove(menu_func_export_iff)
    # bpy.utils.unregister_class(ExportXMF)
    # bpy.types.INFO_MT_file_export.remove(menu_func_export_xmf)


if __name__ == "__main__":
    register()

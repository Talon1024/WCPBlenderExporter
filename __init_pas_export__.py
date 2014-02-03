# Blender WCP IFF source exporter script by Kevin Caccamo
# Copyright © 2013 Kevin Caccamo
# E-mail: kevin@ciinet.org
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, see <http://www.gnu.org/licenses/>.
#
# <pep8-80 compliant>

import OutputPAS_Blender
import bpy

bl_info = {
"name": "WCP/SO IFF Mesh Source File",
"author": "Kevin Caccamo",
"description": "Export to a WCP/SO IFF mesh source file.",
"version": (1, 0),
"blender": (2, 65, 0),
"location": "File > Export",
"warning": "",
"wiki_url": "http://www.ciinet.org/kevin/"
"bl_wcp_exporter/bl_wcp_export_manual.html",
"category": "Import-Export"
}



# ExportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ExportHelper, axis_conversion
from bpy.props import StringProperty, IntProperty, BoolProperty, EnumProperty
from bpy.types import Operator

class ExportPAS(Operator, ExportHelper):
    """Export to a WCPPascal source file"""
    # important since its how bpy.ops.import_test.some_data is constructed
    bl_idname = "export_scene.pas"
    
    bl_label = "Export WCP/SO IFF mesh source file"

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
            description="The number that the MAT texture "
            "indices will start at",
            default=22000,
            subtype="UNSIGNED",
            min=0,
            max=99999990
            )

    apply_modifiers = BoolProperty(
            name = "Apply Modifiers",
            description = "Apply Modifiers to exported model",
            default = True
            )

    active_as_lod0 = BoolProperty(
            name = "Active object is LOD0",
            description = "Use the active object as the LOD 0 mesh",
            default = True
        )

##     generate_bsp = BoolProperty(
##             name = "Generate BSP",
##             description = "Generate a BSP tree "
##             "(for corvette and capship component meshes)",
##             default = False
##         )
##
##    axis_forward = EnumProperty(
##            name="Forward Axis",
##            items=(('X', "X Forward", ""),
##                   ('Y', "Y Forward", ""),
##                   ('Z', "Z Forward", ""),
##                   ('-X', "-X Forward", ""),
##                   ('-Y', "-Y Forward", ""),
##                   ('-Z', "-Z Forward", ""),
##                   ),
##            default='Y',
##            )
##
##    axis_up = EnumProperty(
##            name="Up Axis",
##            items=(('X', "X Up", ""),
##                   ('Y', "Y Up", ""),
##                   ('Z', "Z Up", ""),
##                   ('-X', "-X Up", ""),
##                   ('-Y', "-Y Up", ""),
##                   ('-Z', "-Z Up", ""),
##                   ),
##            default='Z',
##            )
##    
##    output_format = EnumProperty(
##            name="Output Format",
##            items=(('Binary', "Binary IFF Format", ""),
##                   ('Source', "IFF Source Code", "")
##                   ),
##            default='Binary',
##            )

    def execute(self, context):
        ##axis_conversion(self.axis_forward, self.axis_up, "Z", "Y")
        if context.active_object.type == "MESH":
            pass
        else:
            # If the user's active object is not a mesh,
            # use a mesh object named detail-0
            self.active_as_lod0 = False
            print("Active object is not a mesh!"
                  " Using an object named detail-0 instead...")
        try:
            if self.active_as_lod0 == False:
                bpy.data.objects["detail-0"]
            PASFile = open(self.filepath, "x")
            PASFile.close()
        except KeyError:
            print("Unable to find an LOD 0 mesh in the scene!"
                  " Make sure you have an object named 'detail-0'")
        except FileExistsError:
            print("File already exists!")

        print("running write_pas...")
        status = OutputPAS_Blender.write_iff(
                    self.filepath, self.texnum, self.apply_modifiers,
                    self.active_as_lod0)
        if type(status) == tuple:
            self.report(*status)
            return {'CANCELLED'}
        return {'FINISHED'}


# Only needed if you want to add into a dynamic menu
def menu_func_export(self, context):
    self.layout.operator(ExportPAS.bl_idname,
                         text="WCP/SO IFF Mesh Source (.pas)")


def register():
    bpy.utils.register_class(ExportPAS)
    bpy.types.INFO_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_class(ExportPAS)
    bpy.types.INFO_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()

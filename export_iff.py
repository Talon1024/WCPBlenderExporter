# -*- coding: utf8 -*-
# Blender WCP IFF exporter script by Kevin Caccamo
# Copyright © 2013-2015 Kevin Caccamo
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
from . import iff_mesh
from math import sin, cos
from collections import OrderedDict

MAX_NUM_LODS = 3
LOD_NAMES = ["detail-" + str(lod) for lod in range(MAX_NUM_LODS)]
LFLAG_FULLBRIGHT = 2

# Non-critical warnings will be reported to Blender. Critical errors will be
# exceptions.


class KeyWarning(Warning):
    pass


class TypeWarning(Warning):
    pass


class ExportBackend:

    def __init__(self,
                 filepath,
                 start_texnum=22000,
                 apply_modifiers=True,
                 active_obj_as_lod0=True,
                 use_facetex=False,
                 wc_orientation_matrix=None,
                 generate_bsp=False):
        self.filepath = filepath
        self.start_texnum = start_texnum
        self.apply_modifiers = apply_modifiers
        self.active_obj_as_lod0 = active_obj_as_lod0
        self.use_facetex = use_facetex
        self.wc_orientation_matrix = wc_orientation_matrix
        self.generate_bsp = generate_bsp

    def calc_rot_matrix(self, rx, ry, rz):
        """
        Calculate a rotation matrix from a set of rotations
        on the x, y, and z axes.

        Calculates a rotation matrix for each axis,
        and then multiplies the results together.
        Blender's rotation matrix multiplication doesn't work correctly...
        Rotations are in eulers (radians).
        """

        cx = cos(rx)
        sx = sin(rx)
        cy = cos(ry)
        sy = sin(ry)
        cz = cos(rz)
        sz = sin(rz)

        # Thanks to Wikipedia (Rotation matrix) and
        # http://www.idomaths.com/linear_transformation_3d.php
        matrix_x = [[1, 0, 0],
                    [0, cx, sx],
                    [0, -sx, cx]]
        matrix_y = [[cy, 0, -sy],
                    [0, 1, 0],
                    [sy, 0, cy]]
        matrix_z = [[cz, sz, 0],
                    [-sz, cz, 0],
                    [0, 0, 1]]

        # From http://nghiaho.com/?page_id=846: R = ZYX
        rot_matrix = self.multiply_3x3_matrices(matrix_z, matrix_y)
        rot_matrix = self.multiply_3x3_matrices(rot_matrix, matrix_x)
        return rot_matrix

    def multiply_3x3_matrices(self, matrix1, matrix2):
        """
        Multiplies two 3x3 matrices together and
        returns the resulting matrix.
        """
        result_matrix = [

            # First row
            # First row of matrix1 * first column of matrix2
            [matrix1[0][0] * matrix2[0][0] +
             matrix1[0][1] * matrix2[1][0] +
             matrix1[0][2] * matrix2[2][0],

             # First row of matrix1 * second column of matrix2
             matrix1[0][0] * matrix2[0][1] +
             matrix1[0][1] * matrix2[1][1] +
             matrix1[0][2] * matrix2[2][1],

             # First row of matrix1 * third column of matrix2
             matrix1[0][0] * matrix2[0][2] +
             matrix1[0][1] * matrix2[1][2] +
             matrix1[0][2] * matrix2[2][2]],

            # Second row
            # Second row of matrix1 * first column of matrix2
            [matrix1[1][0] * matrix2[0][0] +
             matrix1[1][1] * matrix2[1][0] +
             matrix1[1][2] * matrix2[2][0],

             # Second row of matrix1 * second column of matrix2
             matrix1[1][0] * matrix2[0][1] +
             matrix1[1][1] * matrix2[1][1] +
             matrix1[1][2] * matrix2[2][1],

             # Second row of matrix1 * third column of matrix2
             matrix1[1][0] * matrix2[0][2] +
             matrix1[1][1] * matrix2[1][2] +
             matrix1[1][2] * matrix2[2][2]],

            # Third row
            # Third row of matrix1 * first column of matrix2
            [matrix1[2][0] * matrix2[0][0] +
             matrix1[2][1] * matrix2[1][0] +
             matrix1[2][2] * matrix2[2][0],

             # Third row of matrix1 * second column of matrix2
             matrix1[2][0] * matrix2[0][1] +
             matrix1[2][1] * matrix2[1][1] +
             matrix1[2][2] * matrix2[2][1],

             # Third row of matrix1 * third column of matrix2
             matrix1[2][0] * matrix2[0][2] +
             matrix1[2][1] * matrix2[1][2] +
             matrix1[2][2] * matrix2[2][2]]
        ]
        return result_matrix

    def get_lod_data(self):
        """Get the level of detail data pertinent to the game engine"""
        num_lods = 0

        # Get the LOD data
        lod_data = dict()
        for lod in range(MAX_NUM_LODS):
            ob = None
            lod_ob_name = LOD_NAMES[lod]
            if lod == 0:    # LOD 0 can either be the active object or detail-0
                # If the user wants to use the active object...
                ob = bpy.context.active_object
                if (self.active_obj_as_lod0 and
                        ob.name != lod_ob_name):
                    if ob.type == "MESH":
                        ob = bpy.context.active_object
                        lod_data["LOD-" + str(lod)] = ob
                        num_lods += 1
                    else:
                        error_msg = "Object " + ob.name + " is not a mesh!"
                        warnings.warn(error_msg, TypeWarning)
                        ob = bpy.data.objects[lod_ob_name]
                        try:
                            lod_data["LOD-" + str(lod)] = ob
                            if ob.type != "MESH":
                                error_msg = lod_ob_name + " is not a mesh!"
                                raise TypeError(error_msg)
                            num_lods += 1
                        except KeyError:
                            error_msg = ("Cannot find an object named " +
                                         lod_ob_name + "!")
                            raise KeyError(error_msg)
                else:    # Otherwise, use the detail-0 object
                    ob = bpy.data.objects[lod_ob_name]
                    try:
                        lod_data["LOD-" + str(lod)] = ob
                        if ob.type != "MESH":
                            error_msg = lod_ob_name + " is not a mesh!"
                            raise TypeError(error_msg)
                        num_lods += 1
                    except KeyError:
                        error_msg = ("Cannot find an object named " +
                                     lod_ob_name + "!")
                        raise KeyError(error_msg)
            else:   # Other LODs
                try:
                    ob = bpy.data.objects[lod_ob_name]
                    lod_data["LOD-" + str(lod)] = ob
                    num_lods += 1
                except KeyError:
                    error_msg = "Unable to find a mesh for LOD " + str(lod)
                    warnings.warn(error_msg, KeyWarning)
        lod_data["num_lods"] = num_lods
        return lod_data

    def get_hardpoints(self):
        """
        For all empties named "hp-xxxx" in the scene,
        converts them to hardpoint dictionaries.
        Returns a list of hardpoint dictionaries.
        """
        hardpoints = []
        for o in bpy.data.objects:
            if o.type == "EMPTY" and o.name.startswith("hp-") and not o.hide:
                rot_matrix = self.calc_rot_matrix(
                    o.rotation_euler.x,
                    o.rotation_euler.z,
                    o.rotation_euler.y
                )
                hardpoints.append(
                    {"x": o.location.x,
                     "y": o.location.z,
                     "z": o.location.y,
                     "rot_matrix": rot_matrix,
                     "name": o.name[3:]}
                )
        return hardpoints

    def calc_radius(self, dim):
        """Calculate the radius of the model.

        Radius is calculated by dividing the highest dimension (diameter) by 2.
        """
        max_bb = max(dim)
        radius = max_bb / 2
        return radius

    def calc_dplane(self, vert, facenrm):
        """Calculate the D-Plane of the face.

        vert refers to the first vertex of the face
        facenrm refers to the face normal
        The D-Plane is used by the VISION engine for backface culling
        Thanks to gr1mre4per from CIC for the algorithm!
        """
        dplane = -((facenrm[0] * vert[0]) +
                   (facenrm[1] * vert[1]) +
                   (facenrm[2] * vert[2]))
        return dplane

    def get_first_texture_slot(self, mtl):
        for mtex in reversed(mtl.texture_slots):
            if mtex:
                return mtex
        else:
            return None

    def get_materials(self, lod_data):
        """Convert all of the named material textures to
        texture indices.

        Returns a mapping from material texture filenames
        to texture indices."""
        # Aliases to long function names
        # Filename w/o extension
        get_fname = bpy.path.display_name_from_filepath
        # Filename with extension
        get_bname = bpy.path.basename

        num_lods = lod_data["num_lods"]
        # Use OrderedDict to retain order of texture -> texnum
        # Texture filename -> texture number mapping
        mtl_texnums = OrderedDict()
        # Materials used by the mesh
        used_mtls = []

        # Get all of the material names used in each LOD mesh.
        for lod in range(num_lods):
            mesh = lod_data["LOD-" + str(lod)].to_mesh(
                bpy.context.scene, self.apply_modifiers, "PREVIEW")
            if self.use_facetex:
                active_idx = None
                for idx, texmap in enumerate(mesh.tessface_uv_textures):
                    if texmap.active:
                        active_idx = idx
                        break
                for f in mesh.tessface_uv_textures[active_idx].data:
                    used_mtls.append(get_bname(f.image.filepath))
            else:
                for f in mesh.tessfaces:
                    cur_mtl = mesh.materials[f.material_index].name
                    if cur_mtl not in used_mtls:
                        used_mtls.append(cur_mtl)

        # Get the textures and associate each texture with a material number,
        # beginning at the user's specified starting texture number.
        num_textures = 0
        for mtl_name in used_mtls:
            curr_txnum = self.start_texnum + num_textures
            if self.use_facetex:
                img_bname = get_bname(mtl_name)
                img_fname = get_fname(mtl_name)
                print(img_fname)
                if img_fname.isnumeric():
                    # If the filename is numeric, use it as the
                    # texture index.
                    img_num = int(img_fname)
                    if img_num >= 0 and img_num <= 99999990:
                        if img_num != curr_txnum:
                            mtl_texnums[img_bname] = img_num
                        else:
                            mtl_texnums[img_bname] = curr_txnum
                            print(img_fname, "is already in use! Using",
                                  curr_txnum, "instead.")
                            num_textures += 1
                else:
                    if img_bname not in mtl_texnums.keys():
                        mtl_texnums[img_bname] = curr_txnum
                        num_textures += 1
            else:
                curr_mtl = bpy.data.materials[mtl_name]
                curr_tx = self.get_first_texture_slot(curr_mtl).texture

                if curr_tx.type == "IMAGE":
                    img_bname = get_bname(curr_tx.image.filepath)
                    img_fname = get_fname(curr_tx.image.filepath)
                    if img_fname.isnumeric():
                        # If the filename is numeric, use it as the
                        # texture index.
                        img_num = int(img_fname)
                        if img_num >= 0 and img_num <= 99999990:
                            # What if the user has two numeric image
                            # filenames that are the same number?
                            # i.e. 424242.jpg and 424242.png
                            if img_num not in mtl_texnums.values():
                                mtl_texnums[img_bname] = img_num
                            else:
                                mtl_texnums[img_bname] = curr_txnum
                                print(img_fname, "is already in use! Using",
                                      curr_txnum, "instead.")
                                num_textures += 1
                        else:
                            # If the number is too big,
                            # use the "default" value.
                            mtl_texnums[img_bname] = curr_txnum
                            print(img_fname, "is too big a number",
                                  "to be used as a texture number! Using",
                                  curr_txnum, "instead.")
                            num_textures += 1
                    # If the image filename is not numeric,
                    # refer to the user's starting texture number.
                    else:
                        if img_bname not in mtl_texnums.keys():
                            mtl_texnums[img_bname] = curr_txnum
                            num_textures += 1
                else:
                    error_msg = curr_tx.name + " is not an image texture."
                    raise TypeError(error_msg)
        return mtl_texnums

    def get_txinfo(self, mtl_texnums, as_comment=False):
        """Gets a string showing the Image Filename->Texture number"""
        # Used to make the Image Filename->Material Number list
        # easier to read.
        # max_width = len(max(mtl_texnums.keys(), key=len))
        # Print Image Filename->Material Number information for the
        # user to use as a guide for converting textures.
        tx_info = ""
        for img_fname, texnum in sorted(
                mtl_texnums.items(),
                key=lambda mattex: mattex[1]):
            if as_comment:
                tx_info += "// "
            maxlen = max(map(len, mtl_texnums.keys()))
            tx_info += (
                "{:" + str(maxlen) +
                "} --> {!s:0>8}.mat\n").format(img_fname, texnum)
        return tx_info


class IFFExporter(ExportBackend):

    def export(self):
        """
        Export a .pas file from the Blender scene.
        The model is exported as a .pas file that can be compiled
        by WCPPascal into a WCP/SO format mesh.
        """

        # Aliases to long function names
        # Filename without extension
        get_fname = bpy.path.display_name_from_filepath
        # Filename with extension
        get_bname = bpy.path.basename

        # Get directory path of output file, plus filename without extension
        filename = self.filepath[:self.filepath.rfind(".")]
        modelname = get_fname(self.filepath)

        # Create an IFF mesh object
        imesh = iff_mesh.MeshIff(filename)

        # Get LOD data and number of LODs
        lod_data = self.get_lod_data()
        if type(lod_data) == tuple:  # tuple means error
            return lod_data
        num_lods = lod_data["num_lods"]

        # Get the hardpoints
        hardpoints = self.get_hardpoints()

        # Get texture indices for each material
        mtl_texnums = self.get_materials(lod_data)

        mtl_info_file = open(filename + ".txt", 'w', encoding='utf-8')

        print(self.get_txinfo(mtl_texnums), file=mtl_info_file)

        for lod in range(num_lods):
            bl_mesh = lod_data["LOD-" + str(lod)].to_mesh(
                bpy.context.scene, self.apply_modifiers, "PREVIEW")

            bl_mesh.transform(lod_data["LOD-" + str(lod)].matrix_local)
            if self.wc_orientation_matrix is not None:
                bl_mesh.transform(self.wc_orientation_matrix)

            # Required for using tesselated faces (squares and triangles).
            # I decided to use tessfaces for now to keep it simple,
            # but later I may change my mind, since WCSO supports n-gons.
            bl_mesh.calc_tessface()

            bl_mesh.calc_normals()

            # Get unique normals
            unique_normals = set()

            for f in bl_mesh.tessfaces:
                if f.use_smooth:
                    for v in f.vertices:
                        # If smoothing is enabled, add the vertex normals
                        nx, ny, nz = bl_mesh.vertices[v].normal
                        unique_normals.add((nx, ny, nz))
                # Add the face normal
                nx, ny, nz = f.normal
                unique_normals.add((nx, ny, nz))

            unique_normals = tuple(unique_normals)

            # Get the references to the normals
            fnrmrefs = list()
            vnrmrefs = list()

            # Face normal indices
            for f in bl_mesh.tessfaces:
                nx, ny, nz = f.normal
                fnrmrefs.append(unique_normals.index((nx, ny, nz)))

            # Vertex normal indices
            for v in bl_mesh.vertices:
                nx, ny, nz = v.normal
                try:
                    vnrmrefs.append(unique_normals.index((nx, ny, nz)))
                except ValueError:
                    vnrmrefs.append(0)

            # Create an IFF mesh LOD object for this LOD
            imeshl = iff_mesh.MeshLODForm(lod)

            # Name
            imeshl.set_name(modelname)

            # Vertices
            for v in bl_mesh.vertices:
                vx, vy, vz = v.co[:]
                imeshl.add_vertex(float(-vx), float(vy), float(vz))

            # Normals
            for n in unique_normals:
                nx, ny, nz = n[:]
                imeshl.add_normal(float(-nx), float(ny), float(nz))

            # Vertices on each face
            fnrm_idx = 0
            uv_map = bl_mesh.tessface_uv_textures.active.data
            for f, u in zip(bl_mesh.tessfaces, uv_map):
                for v, uv in zip(reversed(f.vertices), reversed(u.uv)):
                    if f.use_smooth:
                        # If smoothing is enabled, use the vertex normal
                        vtnm_idx = vnrmrefs[v]
                    else:
                        # Otherwise, use the face normal
                        vtnm_idx = fnrmrefs[fnrm_idx]
                    vert_idx = v
                    uv_x, uv_y = uv
                    # -uv_y allows textures to be converted without the
                    # modder having to vertically flip them.
                    imeshl.add_fvrt(vert_idx, vtnm_idx, uv_x, -uv_y)
                fnrm_idx += 1

            # Faces
            fvrt_idx = 0
            for cur_face_idx, cur_face in enumerate(bl_mesh.tessfaces):

                light_flags = 0
                # If the face has a material with an image texture,
                # get the corresponding texture number
                if self.use_facetex:
                    active_idx = None
                    mesh_uvtex = bl_mesh.tessface_uv_textures
                    for idx, texmap in enumerate(mesh_uvtex):
                        if texmap.active:
                            active_idx = idx
                            break
                    facetex = mesh_uvtex[active_idx].data[cur_face_idx]
                    matfilename = get_bname(facetex.image.filepath)
                    texnum = mtl_texnums[matfilename]
                else:
                    facemtl = bl_mesh.materials[cur_face.material_index]
                    facetex = facemtl.active_texture
                    if facetex.type == "IMAGE":
                        matfilename = get_bname(facetex.image.filepath)
                        texnum = mtl_texnums[matfilename]
                    else:
                        # Otherwise, use the default texture number
                        texnum = start_texnum

                    # If the material on the face is shadeless,
                    # set the corresponding lighting bitflag.
                    # More bitflags will be added as they are discovered.
                    # This will not work if you are using facetex, as special
                    # lighting can only be done using materials.
                    if facemtl.use_shadeless:
                        light_flags |= LFLAG_FULLBRIGHT
                    if "light_flags" in facemtl:
                        # If the user has defined a custom value to
                        # use for the lighting bitflag, override the
                        # calculated value with the custom value.
                        try:
                            light_flags = int(facemtl["light_flags"])
                        except ValueError:
                            light_flags = 0
                            print("Cannot convert", facemtl["light_flags"],
                                  "to an integer value!")

                num_verts = len(cur_face.vertices)

                vtnm_idx = fnrmrefs[cur_face_idx]

                # Vertex coordinates and normals are needed
                # in order to calculate the D-Plane.
                first_vert = bl_mesh.vertices[cur_face.vertices[0]].co
                face_nrm = cur_face.normal
                dplane = self.calc_dplane(first_vert, face_nrm)

                imeshl.add_face(vtnm_idx, dplane, texnum, fvrt_idx,
                                num_verts, light_flags)

                fvrt_idx += num_verts

            # Location, radius metadata for this LOD
            loc = lod_data["LOD-" + str(lod)].location
            radius = self.calc_radius(lod_data["LOD-" + str(lod)].dimensions)

            # Center of object
            imeshl.set_center(loc[0], -loc[1], loc[2])

            # Radius
            imeshl.set_radius(radius)

            imesh.add_lod(imeshl)

        # Hardpoints - These will be created from empties prefixed with "hp-"
        for h in hardpoints:
            imesh.add_hardpt(**h)

        # Collision, LOD distance metadata
        try:
            # If there is an object named "collsphr" in the scene,
            # use it for the object's collision sphere.
            collsphr = bpy.data.objects["collsphr"]
            if collsphr.type == "EMPTY":
                print("collsphr object found")
                loc = collsphr.location
                radius = max(collsphr.scale) * collsphr.empty_draw_size
            else:
                print("collsphr object must be an empty")
                loc = lod_data["LOD-0"].location
                radius = self.calc_radius(lod_data["LOD-0"].dimensions)
        except KeyError:
            print("collsphr object not found")
            loc = lod_data["LOD-0"].location
            radius = self.calc_radius(lod_data["LOD-0"].dimensions)
        imesh.make_coll_sphr(loc[0], loc[1], loc[2], radius)
        imesh.write_file_bin()


class XMFExporter(ExportBackend):

    def export(self):
        """
        Export a .pas file from the Blender scene.
        The model is exported as a .pas file that can be compiled
        by WCPPascal into a WCP/SO format mesh.
        """

        # Aliases to long function names
        get_bname = bpy.path.basename  # Filename with extension

        # Get LOD data and number of LODs
        lod_data = self.get_lod_data()
        if type(lod_data) == tuple:  # tuple means error
            return lod_data
        num_lods = lod_data["num_lods"]

        # Get the hardpoints
        hardpoints = self.get_hardpoints()

        # Get filename w/o extension
        filename = bpy.path.display_name_from_filepath(self.filepath)

        # Get texture indices for each material
        mtl_texnums = self.get_materials(lod_data)

        outfile = open(self.filepath, 'w', encoding='utf-8')
        # IFF source file header. If this is not the first line,
        # the file will not compile.
        print('IFF "', filename, '.iff"', '\n',
              sep="", file=outfile)

        print(self.get_txinfo(mtl_texnums, True), file=outfile)

        print('{', '\n',
              ' ' * 2, 'FORM "DETA"', '\n',
              ' ' * 2, '{', '\n',
              ' ' * 4, 'CHUNK "RANG"', '\n',
              ' ' * 4, '{', '\n',
              ' ' * 6, 'float 0.0', '\n',
              ' ' * 6, 'float 400.0', '\n',
              ' ' * 6, 'float 800.0', '\n',
              ' ' * 4, '}', '\n',
              ' ' * 4, 'FORM "MESH"', '\n',
              ' ' * 4, '{', '\n',
              sep='', end='', file=outfile)
        for lod in range(num_lods):
            bl_mesh = lod_data["LOD-" + str(lod)].to_mesh(
                bpy.context.scene, self.apply_modifiers, "PREVIEW")

            bl_mesh.transform(lod_data["LOD-" + str(lod)].matrix_local)
            if self.wc_orientation_matrix is not None:
                bl_mesh.transform(self.wc_orientation_matrix)

            # Required for using tesselated faces (squares and triangles).
            # I decided to use tessfaces for now to keep it simple,
            # but later I may change my mind, since WCSO supports n-gons.
            bl_mesh.calc_tessface()

            bl_mesh.calc_normals()

            # Get unique normals
            unique_normals = set()

            for f in bl_mesh.tessfaces:
                if f.use_smooth:
                    for v in f.vertices:
                        # If smoothing is enabled, add the vertex normals
                        nx, ny, nz = bl_mesh.vertices[v].normal
                        unique_normals.add((nx, ny, nz))
                # Add the face normal
                nx, ny, nz = f.normal
                unique_normals.add((nx, ny, nz))

            unique_normals = tuple(unique_normals)

            # Get the references to the normals
            fnrmrefs = list()
            vnrmrefs = list()

            # Face normal indices
            for f in bl_mesh.tessfaces:
                nx, ny, nz = f.normal
                fnrmrefs.append(unique_normals.index((nx, ny, nz)))

            # Vertex normal indices
            for v in bl_mesh.vertices:
                nx, ny, nz = v.normal
                try:
                    vnrmrefs.append(unique_normals.index((nx, ny, nz)))
                except ValueError:
                    vnrmrefs.append(0)

            # Get the FORM name for this LOD
            lod_num = str(lod).zfill(4)
            print(
                ' ' * 6, 'FORM "', lod_num, '"', '\n',
                ' ' * 6, '{', '\n',
                ' ' * 8, 'FORM "MESH"', '\n',
                ' ' * 8, '{', '\n',
                ' ' * 10, 'FORM "0012"', '\n',  # Mesh format version number
                ' ' * 10, '{', '\n',
                ' ' * 12, 'CHUNK "NAME"', '\n',
                ' ' * 12, '{', '\n',
                ' ' * 14, 'cstring "', filename, '"', '\n',
                sep='', end='', file=outfile)

            # Alias to format method of format string. The format string
            # is being used for nothing more than formatting output values,
            # so I figured I might as well do it this way, plus, it makes
            # code lines shorter.
            lfmt = "long {}\n".format
            ffmt = "float {:.6f}\n".format

            # Vertices
            print(' ' * 12, '}', '\n',
                  ' ' * 12, 'CHUNK "VERT"', '\n',
                  ' ' * 12, '{',
                  sep='', file=outfile)

            for v in bl_mesh.vertices:
                vx, vy, vz = v.co[:]
                print(' ' * 14, ffmt(-vx),  # Vertex X
                      ' ' * 14, ffmt(vy),  # Vertex Y
                      ' ' * 14, ffmt(vz),  # Vertex Z
                      sep='', file=outfile)

            # Normals
            print(' ' * 12, '}', '\n',
                  ' ' * 12, 'CHUNK "VTNM"', '\n',
                  ' ' * 12, '{',
                  sep="", file=outfile)

            for n in unique_normals:
                vx, vy, vz = n[:]
                print(' ' * 14, ffmt(-vx),  # Normal X
                      ' ' * 14, ffmt(vy),  # Normal Y
                      ' ' * 14, ffmt(vz),  # Normal Z
                      sep='', file=outfile)

            # Vertices on each face
            print(' ' * 12, '}', '\n',
                  ' ' * 12, 'CHUNK "FVRT"', '\n',
                  ' ' * 12, '{',
                  sep='', file=outfile)

            fnrm_idx = 0
            uv_map = bl_mesh.tessface_uv_textures.active.data
            for f, u in zip(bl_mesh.tessfaces, uv_map):
                for v, uv in zip(f.vertices, u.uv):
                    if f.use_smooth:
                        # If smoothing is enabled, use the vertex normal
                        vtnm_idx = vnrmrefs[v]
                    else:
                        # Otherwise, use the face normal
                        vtnm_idx = fnrmrefs[fnrm_idx]
                    vert_idx = v
                    uvX, uvY = uv
                    print(' ' * 14, lfmt(vert_idx),  # Reference to VERT
                          ' ' * 14, lfmt(vtnm_idx),  # Reference to VTNM
                          ' ' * 14, ffmt(uvX),
                          # -uvY allows textures to be converted without
                          # the modder having to vertically flip them.
                          ' ' * 14, ffmt(-uvY),
                          sep='', file=outfile)
                fnrm_idx += 1

            # Faces
            print(' ' * 12, '}', '\n',
                  ' ' * 12, 'CHUNK "FACE"', '\n',
                  ' ' * 12, '{',
                  sep='', file=outfile)

            fvrt_idx = 0
            for cur_face_idx, cur_face in enumerate(bl_mesh.tessfaces):
                light_flags = 0

                if self.use_facetex:
                    active_idx = None
                    mesh_uvtex = bl_mesh.tessface_uv_textures
                    for idx, texmap in enumerate(mesh_uvtex):
                        if texmap.active:
                            active_idx = idx
                            break
                    facetex = mesh_uvtex[active_idx].data[cur_face_idx]
                    matfilename = get_bname(facetex.image.filepath)
                    texnum = mtl_texnums[matfilename]
                else:
                    # If the face has a material with an image texture,
                    # get the corresponding texture number
                    facemtl = bl_mesh.materials[cur_face.material_index]
                    facetex = facemtl.active_texture
                    if facetex.type == "IMAGE":
                        matfilename = get_bname(facetex.image.filepath)
                        texnum = mtl_texnums[matfilename]
                    else:
                        # Otherwise, use the default texture number
                        texnum = start_texnum

                    # If the material on the face is shadeless,
                    # set the corresponding lighting bitflag.
                    # More bitflags will be added as they are discovered.
                    if facemtl.use_shadeless:
                        light_flags |= LFLAG_FULLBRIGHT
                    if "light_flags" in facemtl:
                        # If the user has defined a custom value to
                        # use for the lighting bitflag, override the
                        # calculated value with the custom value.
                        try:
                            light_flags = int(facemtl["light_flags"])
                        except ValueError:
                            light_flags = 0
                            print("Cannot convert", facemtl["light_flags"],
                                  "to an integer value!")

                num_verts = len(cur_face.vertices)

                vtnm_idx = fnrmrefs[cur_face_idx]

                # Vertex coordinates and normals are needed
                # in order to calculate the D-Plane.
                first_vert = bl_mesh.vertices[cur_face.vertices[0]].co
                face_nrm = cur_face.normal
                dplane = self.calc_dplane(first_vert, face_nrm)

                print(
                    ' ' * 14, lfmt(vtnm_idx),     # Face normal
                    ' ' * 14, ffmt(dplane),       # D-Plane
                    ' ' * 14, lfmt(texnum),       # Texture number
                    ' ' * 14, lfmt(fvrt_idx),     # Index of face's first FVRT
                    ' ' * 14, lfmt(num_verts),    # Number of vertices
                    ' ' * 14, lfmt(light_flags),  # Lighting flags
                    ' ' * 14, lfmt('$7F0096FF'),  # Unknown
                    sep='', file=outfile
                )
                fvrt_idx += num_verts

            # Location, radius metadata for this LOD
            loc = lod_data["LOD-" + str(lod)].location
            radius = self.calc_radius(lod_data["LOD-" + str(lod)].dimensions)

            # Center of object
            print('            }', '\n',
                  '            CHUNK "CNTR"', '\n',
                  '            {', '\n',
                  ' ' * 14, ffmt(loc[0]),  # Center X
                  ' ' * 14, ffmt(loc[1]),  # Center Y
                  ' ' * 14, ffmt(loc[2]),  # Center Z
                  '            }', '\n',

                  # Radius. Used by object camera
                  ' ' * 12, 'CHUNK "RADI"', '\n',
                  ' ' * 12, '{', '\n',
                  ' ' * 14, ffmt(radius),
                  ' ' * 12, '}', '\n',
                  ' ' * 10, '}', '\n',
                  ' ' * 8, '}', '\n',
                  ' ' * 6, '}', '\n',
                  sep='', file=outfile)
        print(' ' * 4, '}', '\n',
              ' ' * 4, 'FORM "HARD"', '\n',
              ' ' * 4, '{',
              sep='', file=outfile)

        # Hardpoints - These will be created from empties prefixed with "hp-"
        for h in hardpoints:
            print(' ' * 6, 'CHUNK "HARD"', '\n',
                  ' ' * 6, '{', '\n',
                  ' ' * 8, ffmt(h["rot_matrix"][0][0]),
                  ' ' * 8, ffmt(h["rot_matrix"][0][1]),
                  ' ' * 8, ffmt(h["rot_matrix"][0][2]),
                  ' ' * 8, ffmt(h["x"]),     # Hardpoint X
                  ' ' * 8, ffmt(h["rot_matrix"][1][0]),
                  ' ' * 8, ffmt(h["rot_matrix"][1][1]),
                  ' ' * 8, ffmt(h["rot_matrix"][1][2]),
                  ' ' * 8, ffmt(h["y"]),     # Hardpoint Y
                  ' ' * 8, ffmt(h["rot_matrix"][2][0]),
                  ' ' * 8, ffmt(h["rot_matrix"][2][1]),
                  ' ' * 8, ffmt(h["rot_matrix"][2][2]),
                  ' ' * 8, ffmt(h["z"]),     # Hardpoint Z
                  ' ' * 8, 'cstring "', h["name"], '"', '\n',  # Hardpoint name
                  ' ' * 6, '}',
                  sep='', file=outfile)

        # Collision, LOD distance metadata
        try:
            # If there is an object named "collsphr" in the scene,
            # use it for the object's collision sphere.
            collsphr = bpy.data.objects["collsphr"]
            if collsphr.type == "EMPTY":
                print("collsphr object found")
                loc = collsphr.location
                radius = max(collsphr.scale) * collsphr.empty_draw_size
            else:
                print("collsphr object must be an empty")
                loc = lod_data["LOD-0"].location
                radius = self.calc_radius(lod_data["LOD-0"].dimensions)
        except KeyError:
            print("collsphr object not found")
            loc = lod_data["LOD-0"].location
            radius = self.calc_radius(lod_data["LOD-0"].dimensions)
        print(' ' * 4, '}', '\n',
              ' ' * 4, 'FORM "COLL"', '\n',      # Collision info
              ' ' * 4, '{', '\n',
              ' ' * 6, 'CHUNK "SPHR"', '\n',   # Collision Sphere
              ' ' * 6, '{', '\n',
              ' ' * 8, ffmt(loc[0]),   # Center X
              ' ' * 8, ffmt(loc[1]),   # Center Y
              ' ' * 8, ffmt(loc[2]),   # Center Z
              ' ' * 8, ffmt(radius),   # Radius
              ' ' * 6, '}', '\n',
              ' ' * 4, '}', '\n',
              ' ' * 4, 'CHUNK "FAR "', '\n',
              ' ' * 4, '{', '\n',
              ' ' * 6, 'float 0.0', '\n',
              ' ' * 6, 'float 900000.0', '\n',
              ' ' * 4, '}', '\n',
              ' ' * 2, '}', '\n',
              '}', '\n',
              sep='', file=outfile)
        outfile.close()

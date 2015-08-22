# -*- coding: utf8 -*-
# Blender WCP IFF mesh import/export script by Kevin Caccamo
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
import struct
from mathutils import Matrix
from itertools import starmap, count
from os import sep as dirsep
from os.path import normpath, join as joinpath, exists as fexists
from math import radians

MAX_NUM_LODS = 5
LOD_NAMES = ["detail-" + str(lod) for lod in range(MAX_NUM_LODS)]

mfilepath = None  # These are Initialized in ImportBackend constructor
texmats = None


def register_texture(texnum, mat_name=None):
    """Add a texture to the texture reference if it isn't already there.

    Add a texture to the global texture dictionary if it isn't already in it.
    New entries in the dictionary have the texture number as the key, and the
    Blender material as the value. Return the Blender material associated with
    the newly-registered texture, or the existing Blender material if said
    texture is already in the dictionary.

    @param texnum The texture number to register
    @param mat_name The optional name of the material to use. If blank, the
    mesh filename is used.
    """

    def get_teximgs(texnum, mat_name):
        img_extns = ["bmp", "png", "jpg", "jpeg", "tga", "gif", "dds"]

        mfiledir = mfilepath[:mfilepath.rfind(dirsep)]
        mat_path = normpath(joinpath(
            mfiledir, "..{1}mat{1}{0:0>8d}.mat".format(texnum, dirsep)))

        # Search for and load high-quality images in the same folder first.
        for extn in img_extns:
            img_path = joinpath(mfiledir, mat_name + "." + extn)
            if fexists(img_path):
                bl_img = bpy.data.images.load(img_path)
                texmats[texnum][2] = bl_img

                bl_mtexslot = bl_mat.texture_slots.add()
                bl_mtexslot.texture_coords = "UV"
                bl_mtexslot.uv_layer = "UVMap"

                bl_mtex = bpy.data.textures.new(mat_name, "IMAGE")
                bl_mtex.image = bl_img

                bl_mtexslot.texture = bl_mtex
                break
        else:
            print("High-quality texture image not found!",
                  "Searching for MAT texture...")

        print("Looking for MAT texture at", mat_path)

        if fexists(mat_path):
            print("Found MAT file:", mat_path)
            # TODO: Implement reading of MAT files.
            # print("Cannot read MAT files as of now.")
        else:
            # print("MAT texture {0:0>8d}.mat not found!".format(
            #     texnum))
            pass

    if mat_name is None:
        mat_name = mfilepath[mfilepath.rfind(dirsep) + 1:mfilepath.rfind(".")]

    if texnum not in texmats.keys():
        mat_name += str(len(texmats) + 1)
        # print("mat_name:", mat_name)
        bl_mat = bpy.data.materials.new(mat_name)

        # Last element in this list will become the image file path
        texmats[texnum] = [mat_name, bl_mat, None]
        get_teximgs(texnum, mat_name)
    else:
        mat_name += str(len(texmats))
        # print("mat_name:", mat_name)
        bl_mat = texmats[texnum][1]
        if bl_mat is None:
            bl_mat = bpy.data.materials.new(mat_name)
            texmats[texnum][1] = bl_mat
            get_teximgs(texnum, mat_name)
    return bl_mat


def approx_equal(num1, num2, error):
    return (abs(num2 - num1) <= abs(error))


class ImportBackend:

    def __init__(self,
                 filepath,
                 texname,
                 reorient_matrix,
                 import_all_lods=False,
                 use_facetex=False,
                 import_bsp=False):

        global mfilepath
        global texmats

        mfilepath = filepath
        texmats = {}

        self.reorient_matrix = reorient_matrix
        self.import_all_lods = import_all_lods
        self.use_facetex = use_facetex
        self.import_bsp = import_bsp

        if texname.isspace() or texname == "":
            # Get material/texture name from file name
            self.texname = bpy.path.basename(filepath)
            self.texname = self.texname[:self.texname.rfind(".")]
        else:
            self.texname = texname


class LODMesh:

    def __init__(self, texname):
        self._verts = []
        self._norms = []
        self._fvrts = []
        self._faces = []
        self._name = ""
        self.texname = texname
        self.mtlrefs = {}

    def add_vert(self, vert):
        """Add VERT data to this mesh."""
        if len(vert) == 3 and all(map(lambda e: isinstance(e, float), vert)):
            self._verts.append(vert)
        else:
            raise TypeError("{0!r} ain't no vertex!".format(vert))

    def add_norm(self, norm):
        """Add VTNM data to this mesh."""
        if len(norm) == 3 and all(map(lambda e: isinstance(e, float), norm)):
            self._norms.append(norm)
        else:
            raise TypeError("{0!r} ain't no vertex normal!".format(norm))

    def add_fvrt(self, fvrt):
        """Add FVRT data to this mesh."""
        def validate_fvrt(idx, fvrt_el):
            if idx < 2:
                return isinstance(fvrt_el, int)
            else:
                return isinstance(fvrt_el, float)

        if len(fvrt) == 4 and all(starmap(validate_fvrt, enumerate(fvrt))):
            self._fvrts.append(fvrt)
        else:
            raise TypeError("{0!r} ain't no FVRT!".format(fvrt))

    def add_face(self, face):
        """Add FACE data to this mesh."""
        def validate_face(idx, face_el):
            if idx == 1:
                return isinstance(face_el, float)
            else:
                return isinstance(face_el, int)

        if len(face) == 6 and all(starmap(validate_face, enumerate(face))):
            self._faces.append(face)
        else:
            raise TypeError("{0!r} ain't no FACE!".format(face))

    def set_name(self, name):
        """Set the name of this mesh."""
        self._name = name.strip()

    def set_cntr(self, cntr):
        """Set the center point for this mesh."""
        if len(cntr) == 3 and all(map(lambda e: isinstance(e, float), cntr)):
            self._cntr = cntr
        else:
            raise TypeError("{0!r} ain't no CNTR!".format(cntr))

    def edges_from_verts(self, verts):
        """Generates vertex reference tuples for edges."""
        if all(map(lambda e: isinstance(e, int), verts)):
            for idx in range(len(verts)):
                first_idx = verts[idx]
                if (idx + 1) >= len(verts): next_idx = verts[0]
                else: next_idx = verts[idx + 1]
                yield (first_idx, next_idx)
        else:
            raise TypeError("{0!r} ain't vertex references!")

    def to_bl_mesh(self):
        """Take the WC mesh data and convert it to Blender mesh data."""
        assert(
            len(self._verts) > 0 and len(self._norms) > 0 and
            len(self._fvrts) > 0 and len(self._faces) > 0 and
            self._name != "")

        bl_mesh = bpy.data.meshes.new(self._name)
        bl_mesh.vertices.add(len(self._verts))

        for vidx, v in enumerate(self._verts):
            bl_mesh.vertices[vidx].co = v
            bl_mesh.vertices[vidx].co[0] *= -1

        face_edges = []  # The edges (tuples of indices of two verts)
        edge_refs = []  # indices of edges of faces, as lists per face

        for fidx, f in enumerate(self._faces):

            # used_fvrts = []
            cur_face_verts = []

            for fvrt_ofs in range(f[4]):  # f[4] is number of FVRTS of the face

                cur_fvrt = f[3] + fvrt_ofs  # f[3] is index of first FVRT
                cur_face_verts.append(self._fvrts[cur_fvrt][0])

                bl_mesh.vertices[self._fvrts[cur_fvrt][0]].normal = (
                    self._norms[self._fvrts[cur_fvrt][1]])

                bl_mesh.vertices[self._fvrts[cur_fvrt][0]].normal[0] *= -1
                # used_fvrts.append(f[3] + fvrt_ofs)
            edge_refs.append([])

            for ed in self.edges_from_verts(tuple(reversed(cur_face_verts))):
                if (ed not in face_edges and
                        tuple(reversed(ed)) not in face_edges):
                    eidx = len(face_edges)
                    face_edges.append(ed)
                else:
                    if face_edges.count(ed) == 1:
                        eidx = face_edges.index(ed)
                    else:
                        eidx = face_edges.index(tuple(reversed(ed)))
                edge_refs[fidx].append(eidx)

            if f[2] in texmats.keys():
                if texmats[f[2]][0] not in bl_mesh.materials:
                    self.mtlrefs[f[2]] = len(bl_mesh.materials)
                    bl_mesh.materials.append(texmats[f[2]][1])

        bl_mesh.edges.add(len(face_edges))
        for eidx, ed in enumerate(face_edges):
            bl_mesh.edges[eidx].vertices = ed

        bl_mesh.polygons.add(len(self._faces))
        bl_mesh.uv_textures.new("UVMap")
        num_loops = 0

        for fidx, f in enumerate(self._faces):

            cur_face_fvrts = self._fvrts[f[3]:f[3] + f[4]]
            f_verts = [fvrt[0] for fvrt in cur_face_fvrts]
            f_uvs = [
                (fvrt[2], 1 - fvrt[3]) for fvrt in reversed(cur_face_fvrts)]
            f_edgerefs = edge_refs[fidx]
            f_startloop = num_loops

            bl_mesh.polygons[fidx].vertices = f_verts

            # Assign corresponding material to polygon
            bl_mesh.polygons[fidx].material_index = self.mtlrefs[f[2]]
            # Assign corresponding image to UV image texture (AKA facetex)
            bl_mesh.uv_texture_stencil.data[fidx].image = texmats[f[2]][2]

            assert(len(f_verts) == len(f_edgerefs) == f[4])

            # print("Face", fidx, "loop_total:", f[4])

            # The edges were generated from a set of vertices in reverse order.
            # Since we're getting the vertices from the FVRTs in forward order,
            # only reverse the vertices.
            for fvidx, vrt, edg in zip(
                    count(), reversed(f_verts), f_edgerefs):
                bl_mesh.loops.add(1)
                bl_mesh.loops[num_loops].edge_index = edg
                bl_mesh.loops[num_loops].vertex_index = vrt

                # print("Loop", num_loops, "vertex index:", vrt)
                # print("Loop", num_loops, "edge index:", edg)
                # print("Edge", edg, "vertices",
                #       bl_mesh.edges[edg].vertices[0],
                #       bl_mesh.edges[edg].vertices[1])

                bl_mesh.uv_layers["UVMap"].data[num_loops].uv = f_uvs[fvidx]
                num_loops += 1

            bl_mesh.polygons[fidx].loop_start = f_startloop
            bl_mesh.polygons[fidx].loop_total = f[4]

        return bl_mesh

    def debug_info(self):
        for data in [self._verts, self._norms, self._fvrts, self._faces,
                     self._name]:
            pass
            # print("length of data:", len(data))


class Hardpoint:

    def __init__(self, pos_data, name):
        # Initialize rotation matrix data structure
        # so we don't get access violations.
        self._rot_matrix = [
            [None, None, None],
            [None, None, None],
            [None, None, None]
        ]
        self._rot_matrix[0][0] = pos_data[0]
        self._rot_matrix[0][1] = pos_data[1]
        self._rot_matrix[0][2] = pos_data[2]
        self._x = pos_data[3]
        self._rot_matrix[1][0] = pos_data[4]
        self._rot_matrix[1][1] = pos_data[5]
        self._rot_matrix[1][2] = pos_data[6]
        self._y = pos_data[7]
        self._rot_matrix[2][0] = pos_data[8]
        self._rot_matrix[2][1] = pos_data[9]
        self._rot_matrix[2][2] = pos_data[10]
        self._z = pos_data[11]
        self._name = name

    def to_bl_obj(self):
        bl_obj = bpy.data.objects.new("hp-" + self._name, None)
        bl_obj.empty_draw_type = "ARROWS"

        matrix_rot = Matrix(self._rot_matrix).to_4x4()

        # Convert position/rotation from WC
        euler_rot = matrix_rot.to_euler("XYZ")
        euler_rot.y, euler_rot.z = -euler_rot.z, -euler_rot.y
        euler_rot.x *= -1

        matrix_rot = euler_rot.to_matrix().to_4x4()
        matrix_loc = Matrix.Translation((self._x, self._z, self._y))

        bl_obj.matrix_basis = matrix_loc * matrix_rot
        return bl_obj


class IFFImporter(ImportBackend):

    def read_lod_data(self, major_form):
        mjrf_bytes_read = 4
        # Read all LODs
        while mjrf_bytes_read < major_form["length"]:
            lod_form = self.read_data()
            mjrf_bytes_read += 12
            lod_lev = lod_form["name"].decode("iso-8859-1").lstrip("0")
            if lod_lev == "": lod_lev = 0
            else: lod_lev = int(lod_lev)

            self.skip_data()
            mjrf_bytes_read += 12

            mjrf_bytes_read += self.read_mesh_data(lod_lev)

            print(
                "mjr form length:", major_form["length"],
                "mjr form read:", mjrf_bytes_read,
                "current position:", self.iff_file.tell()
            )

    def read_mesh_data(self, lod_level):
        lodm = LODMesh(self.texname)

        geom = self.read_data()
        geom_bytes_read = 4
        # Mesh version. In most cases, it will be 12
        mvers = geom["name"].decode("iso-8859-1").lstrip("0")
        if mvers == "": mvers = 0
        else: mvers = int(mvers)

        print("Mesh format is", mvers)

        while geom_bytes_read < geom["length"]:
            geom_data = self.read_data()
            geom_bytes_read += geom_data["length"] + 8

            # RADI and NORM chunks are ignored

            if geom_data["name"] == b"NAME":
                name_str = self.read_cstring(geom_data["data"], 0)
                lodm.set_name(name_str)

            elif geom_data["name"] == b"VERT":
                vert_idx = 0
                while vert_idx * 12 < geom_data["length"]:
                    lodm.add_vert(struct.unpack_from(
                        "<fff", geom_data["data"], vert_idx * 12))
                    vert_idx += 1

            # Most 3D models by fans don't have a NORM chunk, but most 3D
            # models from the original game do.

            elif geom_data["name"] == b"VTNM":
                vtnm_idx = 0
                while vtnm_idx * 12 < geom_data["length"]:
                    lodm.add_norm(struct.unpack_from(
                        "<fff", geom_data["data"], vtnm_idx * 12))
                    vtnm_idx += 1

            elif geom_data["name"] == b"FVRT":
                fvrt_idx = 0
                while fvrt_idx * 16 < geom_data["length"]:
                    lodm.add_fvrt(struct.unpack_from(
                        "<iiff", geom_data["data"], fvrt_idx * 16))
                    fvrt_idx += 1

            elif geom_data["name"] == b"FACE":
                face_idx = 0
                while face_idx * 28 < geom_data["length"]:
                    # Multiply by 28 to skip "unknown2" value
                    face_data = struct.unpack_from(
                        "<ifiiii", geom_data["data"], face_idx * 28)
                    lodm.add_face(face_data)
                    register_texture(face_data[2])
                    face_idx += 1

            elif geom_data["name"] == b"CNTR":
                lodm.set_cntr(struct.unpack("<fff", geom_data["data"]))

            # print(
            #     "geom length:", geom["length"],
            #     "geom read:", geom_bytes_read,
            #     "current position:", self.iff_file.tell()
            # )
        try:
            bl_mesh = lodm.to_bl_mesh()
            if isinstance(self.reorient_matrix, Matrix):
                bl_mesh.transform(self.reorient_matrix)
            bl_ob = bpy.data.objects.new(LOD_NAMES[lod_level], bl_mesh)
            bpy.context.scene.objects.link(bl_ob)
        except AssertionError:
            lodm.debug_info()
        geom_bytes_read += 8  # This function used to return mjrf_bytes_read
        return geom_bytes_read

    def read_hard_data(self, major_form):
        mjrf_bytes_read = 4
        while mjrf_bytes_read < major_form["length"]:
            hardpt_chunk = self.read_data()
            # ALWAYS add 8 when you read a chunk (because the chunk header is
            # 8 bytes long)
            mjrf_bytes_read += hardpt_chunk["length"] + 8

            hardpt_data = struct.unpack_from(
                "<ffffffffffff", hardpt_chunk["data"], 0)

            hardpt_name_ofs = 48
            hardpt_name = self.read_cstring(
                hardpt_chunk["data"], hardpt_name_ofs)

            hardpt = Hardpoint(hardpt_data, hardpt_name)
            bl_ob = hardpt.to_bl_obj()

            bpy.context.scene.objects.link(bl_ob)

    def read_coll_data(self):
        coll_data = self.read_data()
        if coll_data["name"] == b"SPHR":
            bl_obj = bpy.data.objects.new("collsphr", None)
            bl_obj.empty_draw_type = "SPHERE"
            x, y, z, r = struct.unpack("<ffff", coll_data["data"])
            bl_obj.scale = r, r, r
            bl_obj.location = -x, z, y
            bpy.context.scene.objects.link(bl_obj)

    def read_cstring(self, data, ofs):
        cstring = bytearray()
        the_byte = 1
        while the_byte != 0:
            the_byte = data[ofs]
            if the_byte == 0: break
            cstring.append(the_byte)
            ofs += 1
        return cstring.decode("iso-8859-1")

    def load(self):
        self.iff_file = open(mfilepath, "rb")
        root_form = self.read_data()
        if root_form["type"] == "form":
            print("Root form is:", root_form["name"])
            if root_form["name"] == b"DETA":
                mjrfs_read = 4
                while mjrfs_read < root_form["length"]:
                    major_form = self.read_data()
                    mjrfs_read += major_form["length"] + 8
                    # print("Reading major form:", major_form["name"])
                    if major_form["name"] == b"RANG":
                        pass  # RANG data is useless to Blender.
                    elif major_form["name"] == b"MESH":
                        self.read_lod_data(major_form)
                    elif major_form["name"] == b"HARD":
                        self.read_hard_data(major_form)
                    elif major_form["name"] == b"COLL":
                        self.read_coll_data()
                    elif major_form["name"] == b"FAR ":
                        pass  # FAR data is useless to Blender.
                    else:
                        # print("Unknown major form:", major_form["name"])
                        pass

                    # print(
                    #     "root form length:", root_form["length"],
                    #     "root form bytes read:", mjrfs_read
                    # )
            elif root_form["name"] == b"MESH":
                self.read_mesh_data(0)
            else:
                raise TypeError(
                    "This file isn't a mesh! (root form is {})".format(
                        root_form["name"].decode("iso-8859-1")))
        else:
            raise TypeError("This file isn't a mesh! (root is not a form)")

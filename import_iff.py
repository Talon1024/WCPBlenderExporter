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
import struct
from . import iff_read, iff_mesh, mat_read
from mathutils import Matrix
from itertools import starmap, count
from os import sep as dirsep
from os.path import normpath, join as joinpath, exists as fexists
from math import radians

MAX_NUM_LODS = 7
# MAIN_LOD_NAMES = ["detail-" + str(lod) for lod in range(MAX_NUM_LODS)]
CHLD_LOD_NAMES = ["{{0}}-lod{0:d}".format(lod) for lod in range(MAX_NUM_LODS)]

mfilepath = None  # These are Initialized in ImportBackend constructor
texmats = None


class ValueWarning(Warning):
    pass


def register_texture(texnum, mat_name=None, read_mats=True):
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

    bl_mat = ""

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

            if read_mats:
                mat_reader = mat_read.MATReader(mat_path)
                mat_reader.read()
                mat_reader.flip_y()
                bl_img = bpy.data.images.new(
                    mat_path[mat_path.rfind(dirsep):],
                    mat_reader.img_width,
                    mat_reader.img_height,
                    True
                )
                bl_img.pixels = [x / 255 for x in mat_reader.pixels.tolist()]

                bl_mtexslot = bl_mat.texture_slots.add()
                bl_mtexslot.texture_coords = "UV"
                bl_mtexslot.uv_layer = "UVMap"

                bl_mtex = bpy.data.textures.new(mat_name, "IMAGE")
                bl_mtex.image = bl_img

                bl_mtexslot.texture = bl_mtex
        else:
            print("MAT texture {0:0>8d}.mat not found!".format(texnum))
        if "textureRefDoc" in bpy.data.texts:
            textureRefDoc = bpy.data.texts["textureRefDoc"]
        else:
            textureRefDoc = bpy.data.texts.new("textureRefDoc")
        textureRefDoc.write("{0:0>8d}.mat -> {1}\n".format(texnum, mat_name))

    if mat_name is None:
        mat_name = mfilepath[mfilepath.rfind(dirsep) + 1:mfilepath.rfind(".")]

    if texnum not in texmats.keys():
        mat_name += str(len(texmats) + 1)
        # print("mat_name:", mat_name)
        bl_mat = bpy.data.materials.new(mat_name)

        texmats[texnum] = [mat_name, bl_mat, None]
        if (texnum & 0xff000000) == 0x7f000000:
            # Flat colour material
            bl_mat.diffuse_color = [
                float(x + 1) / 256 for x in
                struct.unpack_from("<BBB", texnum.to_bytes(4, 'big'), 1)
            ]
        else:
            # Last element in this list will become the image file path
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
                 import_bsp=False,
                 read_mats=False):

        global mfilepath
        global texmats

        mfilepath = filepath
        texmats = {}

        self.reorient_matrix = reorient_matrix
        self.import_all_lods = import_all_lods
        self.use_facetex = use_facetex
        self.import_bsp = import_bsp
        self.read_mats = read_mats
        self.dranges = None
        self.lod_objs = []
        self.mdl_base_name = ""

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
        self._cntr = (0.0, 0.0, 0.0)
        self._radi = 0.0
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

    def set_radi(self, radi):
        """Set the radius of this mesh."""
        if not isinstance(radi, float):
            raise TypeError("{0!r} is not a valid radius!".format(radi))
        self._radi = radi

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
        print("Oops! Something didn't work properly.")
        # banner = "Oops! Something didn't work properly. Maybe you can "
        # "find out what the issue is. Press ctrl-D to exit the REPL."
        # import code
        # code.interact(banner=banner, local=locals())


class IFFImporter(ImportBackend):

    def read_rang_chunk(self, rang_chunk):
        if rang_chunk["length"] % 4 != 0:
            raise ValueError("RANG chunk has an invalid length!")
        num_dranges = rang_chunk["length"] // 4
        dranges = struct.unpack("<" + ("f" * num_dranges), rang_chunk["data"])
        return dranges

    def parse_major_mesh_form(self, mesh_form):
        mjrmsh_read = 4
        # Read all LODs
        while mjrmsh_read < mesh_form["length"]:
            lod_form = self.iff_reader.read_data()
            lod_lev = int(lod_form["name"].decode("ascii"))

            mnrmsh = self.iff_reader.read_data()
            if mnrmsh["type"] == "form" and mnrmsh["name"] == b"MESH":
                self.parse_minor_mesh_form(mnrmsh, lod_lev)

            mjrmsh_read += 8 + lod_form["length"]
            print("mjrmsh_read:", mjrmsh_read, "of", mesh_form["length"])

    def parse_minor_mesh_form(self, mesh_form, lod_lev=0):
        lodm = LODMesh(self.texname)

        mnrmsh_read = 4

        vers_form = self.iff_reader.read_data()
        mesh_vers = int(vers_form["name"].decode("ascii"))
        mnrmsh_read += 12

        print("---------- LOD {} (version {}) ----------".format(
            lod_lev, mesh_vers
        ))

        vec3_struct = "<fff"
        fvrt_struct = "<iiff"
        face_struct = "<ifiiii"
        # Use 28 to skip the "unknown2" value, present in mesh versions 11+
        face_size = 28 if mesh_vers >= 11 else 24

        while mnrmsh_read < mesh_form["length"]:
            geom_data = self.iff_reader.read_data()
            mnrmsh_read += 8 + geom_data["length"]
            print("mnrmsh_read:", mnrmsh_read, "of", mesh_form["length"])

            # RADI and NORM chunks are ignored

            # Internal name of "minor" mesh/LOD mesh
            if geom_data["name"] == b"NAME":
                name_str = self.read_cstring(geom_data["data"], 0)
                if self.mdl_base_name == "":
                    self.mdl_base_name = name_str
                lodm.set_name(name_str)

            # Vertices
            elif geom_data["name"] == b"VERT":
                vert_idx = 0
                while vert_idx * 12 < geom_data["length"]:
                    lodm.add_vert(struct.unpack_from(
                        vec3_struct, geom_data["data"], vert_idx * 12))
                    vert_idx += 1

            # Vertex normals.
            elif geom_data["name"] == b"VTNM" and mesh_vers != 9:
                vtnm_idx = 0
                while vtnm_idx * 12 < geom_data["length"]:
                    lodm.add_norm(struct.unpack_from(
                        vec3_struct, geom_data["data"], vtnm_idx * 12))
                    vtnm_idx += 1

            # Vertex normals (mesh version 9).
            elif geom_data["name"] == b"NORM" and mesh_vers == 9:
                vtnm_idx = 0
                while vtnm_idx * 12 < geom_data["length"]:
                    lodm.add_norm(struct.unpack_from(
                        vec3_struct, geom_data["data"], vtnm_idx * 12))
                    vtnm_idx += 1

            # Vertices for each face
            elif geom_data["name"] == b"FVRT":
                fvrt_idx = 0
                while fvrt_idx * 16 < geom_data["length"]:
                    lodm.add_fvrt(struct.unpack_from(
                        fvrt_struct, geom_data["data"], fvrt_idx * 16))
                    fvrt_idx += 1

            # Face info
            elif geom_data["name"] == b"FACE":
                face_idx = 0
                while face_idx * face_size < geom_data["length"]:
                    face_data = struct.unpack_from(
                        face_struct, geom_data["data"], face_idx * face_size)
                    lodm.add_face(face_data)
                    register_texture(face_data[2], read_mats=self.read_mats)
                    face_idx += 1

            # Center point
            elif geom_data["name"] == b"CNTR":
                lodm.set_cntr(struct.unpack(vec3_struct, geom_data["data"]))

            # print(
            #     "geom length:", geom["length"],
            #     "geom read:", geom_bytes_read,
            #     "current position:", self.iff_file.tell()
            # )
        try:
            bl_mesh = lodm.to_bl_mesh()
            if isinstance(self.reorient_matrix, Matrix):
                bl_mesh.transform(self.reorient_matrix)
            bl_obname = CHLD_LOD_NAMES[lod_lev].format(self.mdl_base_name)
            bl_ob = bpy.data.objects.new(bl_obname, bl_mesh)
            bpy.context.scene.objects.link(bl_ob)
            if lod_lev > 0:
                # Set drange custom property
                try:
                    bl_ob["drange"] = self.dranges[lod_lev]
                except IndexError:
                    try:
                        del bl_ob["drange"]
                    except KeyError:
                        pass
            self.lod_objs.append(bl_ob)
        except AssertionError:
            lodm.debug_info()

    def read_hard_data(self, major_form):
        mjrf_bytes_read = 4
        while mjrf_bytes_read < major_form["length"]:
            hardpt_chunk = self.iff_reader.read_data()
            mjrf_bytes_read += hardpt_chunk["length"] + 8

            hardpt = iff_mesh.Hardpoint.from_chunk(hardpt_chunk["data"])
            bl_ob = hardpt.to_bl_obj()

            bpy.context.scene.objects.link(bl_ob)
            bl_ob.parent = self.lod_objs[0]

    def read_coll_data(self):
        coll_data = self.iff_reader.read_data()
        if coll_data["name"] == b"SPHR":
            coll_sphere = iff_mesh.Sphere.from_sphr_chunk(coll_data["data"])

            bl_obj = coll_sphere.to_bl_obj("collsphr")
            bpy.context.scene.objects.link(bl_obj)
            bl_obj.parent = self.lod_objs[0]

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
        self.iff_reader = iff_read.IffReader(mfilepath)
        root_form = self.iff_reader.read_data()
        if root_form["type"] == "form":
            print("Root form is:", root_form["name"])
            if root_form["name"] == b"DETA":
                mjrfs_read = 4
                while mjrfs_read < root_form["length"]:
                    major_form = self.iff_reader.read_data()
                    mjrfs_read += major_form["length"] + 8
                    # print("Reading major form:", major_form["name"])
                    if major_form["name"] == b"RANG":
                        self.dranges = self.read_rang_chunk(major_form)
                    elif major_form["name"] == b"MESH":
                        self.parse_major_mesh_form(major_form)
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
                self.parse_minor_mesh_form(root_form)
            else:
                self.iff_reader.close()
                raise TypeError(
                    "This file isn't a mesh! (root form is {})".format(
                        root_form["name"].decode("iso-8859-1")))
        else:
            self.iff_reader.close()
            raise TypeError("This file isn't a mesh! (root is not a form)")
        self.iff_reader.close()

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
import struct
from mathutils import Matrix
from itertools import starmap, count
from os.path import exists as fexists

MAX_NUM_LODS = 3
LOD_NAMES = ["detail-" + str(lod) for lod in range(MAX_NUM_LODS)]


def approx_equal(num1, num2, error):
    if abs(num2 - num1) <= abs(error): return True
    else: return False


class ImportBackend:

    def __init__(self,
                 filepath,
                 texname,
                 reorient_matrix,
                 import_all_lods=False,
                 use_facetex=False,
                 import_bsp=False):
        self.filepath = filepath
        self.reorient_matrix = reorient_matrix
        self.import_all_lods = import_all_lods
        self.use_facetex = use_facetex
        self.import_bsp = import_bsp

        if texname.isspace():
            self.texname = "Untitled"
        else:
            self.texname = texname


class LODMesh:

    def __init__(self, texname, texdict):
        self._verts = []
        self._norms = []
        self._fvrts = []
        self._faces = []
        self._name = ""
        self.texname = texname
        self.texdict = texdict

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

    def make_loops(self, edges, edgeidxs):
        """Generates loops for vertices and edges in order to make faces."""
        assert(len(edges) == len(edgeidxs))
        # print(repr(edges), repr(edgeidxs))
        my_edges = [sorted(e) for e in edges]
        my_edges = sorted(my_edges, key=lambda e: e[0])
        used_verts = []
        used_edges = []
        for e, eidx in zip(my_edges, edgeidxs):
            if eidx not in used_edges:
                # used_edges.append(eidx)
                # yield (eidx, e[0])
                if e[0] not in used_verts:
                    used_edges.append(eidx)
                    used_verts.append(e[0])
                    yield (eidx, e[0])
                elif e[1] not in used_verts:
                    used_edges.append(eidx)
                    used_verts.append(e[1])
                    yield (eidx, e[1])
                else:
                    print(
                        "Potential problem encountered!!",
                        "edges: {!r}, edgeidxs: {!r}".format(edges, edgeidxs),
                        "e: {!r}, eidx: {!r}".format(e, eidx),
                        "used_verts: {!r}, used_edges: {!r}".format(
                            used_verts, used_edges), sep="\n")
                    raise StopIteration()

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
            for ed in self.edges_from_verts(cur_face_verts):
                if ed not in face_edges:
                    eidx = len(face_edges)
                    face_edges.append(ed)
                else:
                    eidx = face_edges.index(ed)
                edge_refs[fidx].append(eidx)
            if f[2] not in self.texdict.keys():
                mat_name = self.texname + str(len(self.texdict) + 1)
                self.texdict[f[2]] = (len(bl_mesh.materials), mat_name)
                texture_available = False

                if fexists("../mat/{0:0>8d}.mat".format(f[2])):
                    # Read MAT file
                    # TODO: implement reading of MAT files.
                    print("Cannot read MAT files.")
                    texture_available = False
                else:
                    img_exts = ["png", "jpg", "bmp", "jpeg", "tga"]
                    for ext in img_exts:
                        img_fname = "{}.{}".format(mat_name, ext)
                        if fexists(img_fname):
                            bl_img = bpy.data.images.load(img_fname)
                            texture_available = True
                            break
                    else:
                        texture_available = False

                bl_mat = bpy.data.materials.new(mat_name)
                bl_mesh.materials.append(bl_mat)

                if texture_available:
                    bl_tex = bpy.data.textures.new(mat_name, "IMAGE")
                    bl_tex.image = bl_img
                    # Assign image to image texture
                    bl_mat.texture_slots.add(1)
                    bl_mat.texture_slots[0].mapping = "FLAT"
                    bl_mat.texture_slots[0].texture_coords = "UV"
                    bl_mat.texture_slots[0].use = True
                    bl_mat.texture_slots[0].texture = bl_tex
        bl_mesh.edges.add(len(face_edges))
        for eidx, ed in enumerate(face_edges):
            bl_mesh.edges[eidx].vertices = ed
        bl_mesh.polygons.add(len(self._faces))
        num_loops = 0
        for fidx, f in enumerate(self._faces):
            bl_mesh.polygons[fidx].material_index = self.texdict[f[2]][0]
            f_verts = [fvrt[0] for fvrt in self._fvrts[f[3]:f[3] + f[4]]]
            # f_edges = [face_edges[eidx] for eidx in edge_refs[fidx]]
            f_edgerefs = edge_refs[fidx]
            bl_mesh.polygons[fidx].vertices = f_verts
            f_startloop = num_loops
            assert(len(f_verts) == len(f_edgerefs) == f[4])
            for vrt, edg in zip(f_verts, f_edgerefs):
                bl_mesh.loops.add(1)
                bl_mesh.loops[num_loops].edge_index = edg
                bl_mesh.loops[num_loops].vertex_index = vrt
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
        bl_obj.location = self._x, self._y, self._z
        bl_obj.rotation_euler = Matrix(self._rot_matrix).to_euler("XYZ")
        return bl_obj


class IFFImporter(ImportBackend):

    iff_heads = [b"FORM", b"CAT ", b"LIST"]

    def skip_data(self):
        orig_pos = self.iff_file.tell()
        head = self.iff_file.read(4)
        if head in self.iff_heads:
            self.iff_file.read(8)
        elif head.isalnum() or head == b"FAR ":
            length = struct.unpack(">i", self.iff_file.read(4))[0]
            self.iff_file.read(length)
        else:
            raise TypeError("This file is not a valid IFF file!")
        del orig_pos
        del head
        return None

    def read_data(self):
        orig_pos = self.iff_file.tell()
        head = self.iff_file.read(4)
        if head in self.iff_heads:
            length = (struct.unpack(">i", self.iff_file.read(4))[0])
            name = self.iff_file.read(4)
            return {
                "type": "form",
                "length": length,
                "name": name,
                "offset": orig_pos
            }
        elif head.isalnum() or head == b"FAR ":
            name = head
            length = struct.unpack(">i", self.iff_file.read(4))[0]
            data = self.iff_file.read(length)

            # IFF Chunks and FORMs are aligned at even offsets
            if self.iff_file.tell() % 2 == 1:
                self.iff_file.read(1)
                length += 1

            return {
                "type": "chunk",
                "length": length,
                "name": name,
                "offset": orig_pos,
                "data": data
            }
        else:
            raise TypeError("Tried to read an invalid IFF file!")
        return None  # Shouldn't be reachable

    def read_mesh_data(self, major_form):
        texdict = {}

        mjrf_bytes_read = 4
        # Read all LODs
        while mjrf_bytes_read < major_form["length"]:
            lod_form = self.read_data()
            mjrf_bytes_read += 12
            lod_lev = lod_form["name"].decode("iso-8859-1").lstrip("0")
            if lod_lev == "": self.cur_lod = 0
            else: self.cur_lod = int(lod_lev)

            lodm = LODMesh(self.texname, texdict)

            self.skip_data()  # Skip a MESH form
            mjrf_bytes_read += 12
            geom = self.read_data()
            mjrf_bytes_read += 12

            # Mesh version. In most cases, it will be 12
            mvers = geom["name"].decode("iso-8859-1").lstrip("0")
            if mvers == "": mvers = 0
            else: mvers = int(mvers)

            geom_chunks = [
                b"NAME",
                b"VERT", b"VTNM", b"FVRT", b"FACE",
                b"CNTR", b"RADI"
            ]
            geom_chunks_read = 0

            while geom_chunks_read < len(geom_chunks):
                geom_data = self.read_data()
                mjrf_bytes_read += geom_data["length"] + 8
                # Ignore RADI
                if geom_data["name"] == geom_chunks[0]:  # NAME
                    name_str = self.read_cstring(geom_data["data"], 0)
                    lodm.set_name(name_str)
                elif geom_data["name"] == geom_chunks[1]:  # VERT
                    vert_idx = 0
                    while vert_idx * 12 < geom_data["length"]:
                        lodm.add_vert(struct.unpack_from(
                            "<fff", geom_data["data"], vert_idx * 12))
                        vert_idx += 1
                elif geom_data["name"] == geom_chunks[2]:  # VTNM
                    vtnm_idx = 0
                    while vtnm_idx * 12 < geom_data["length"]:
                        lodm.add_norm(struct.unpack_from(
                            "<fff", geom_data["data"], vtnm_idx * 12))
                        vtnm_idx += 1
                elif geom_data["name"] == geom_chunks[3]:  # FVRT
                    fvrt_idx = 0
                    while fvrt_idx * 16 < geom_data["length"]:
                        lodm.add_fvrt(struct.unpack_from(
                            "<iiff", geom_data["data"], fvrt_idx * 16))
                        fvrt_idx += 1
                elif geom_data["name"] == geom_chunks[4]:  # FACE
                    face_idx = 0
                    while face_idx * 28 < geom_data["length"]:
                        # Multiply by 28 to skip "unknown2" value
                        lodm.add_face(struct.unpack_from(
                            "<ifiiii", geom_data["data"], face_idx * 28))
                        face_idx += 1
                elif geom_data["name"] == geom_chunks[5]:  # CNTR
                    lodm.set_cntr(struct.unpack("<fff", geom_data["data"]))
                geom_chunks_read += 1
                print(
                    "mjr form length:", major_form["length"],
                    "mjr form read:", mjrf_bytes_read,
                    "current position:", self.iff_file.tell()
                )
            try:
                bl_mesh = lodm.to_bl_mesh()
                if isinstance(self.reorient_matrix, Matrix):
                    bl_mesh.transform(self.reorient_matrix)
                bl_ob = bpy.data.objects.new(LOD_NAMES[self.cur_lod], bl_mesh)
                bpy.context.scene.objects.link(bl_ob)
            except AssertionError:
                lodm.debug_info()

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
            bl_obj.location = x, y, z
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
        self.iff_file = open(self.filepath, "rb")
        root_form = self.read_data()
        if root_form["type"] == "form" and root_form["name"] == b"DETA":
            mjrfs_read = 4
            while mjrfs_read < root_form["length"]:
                major_form = self.read_data()
                mjrfs_read += major_form["length"] + 8
                print("Reading major form:", major_form["name"])
                if major_form["name"] == b"RANG":
                    pass  # RANG data is useless to Blender.
                elif major_form["name"] == b"MESH":
                    self.read_mesh_data(major_form)
                elif major_form["name"] == b"HARD":
                    self.read_hard_data(major_form)
                elif major_form["name"] == b"COLL":
                    self.read_coll_data()
                elif major_form["name"] == b"FAR ":
                    pass  # FAR data is useless to Blender.
                else:
                    print("Unknown major form:", major_form["name"])

                # print(
                #     "root form length:", root_form["length"],
                #     "root form bytes read:", mjrfs_read
                # )
        else:
            raise TypeError("This file isn't a mesh!")

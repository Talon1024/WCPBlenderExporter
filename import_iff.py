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
from mathutils import Vector, Matrix
from itertools import starmap
from collections import OrderedDict
from os.path import exists as fexists

MAX_NUM_LODS = 3
LOD_NAMES = ["detail-" + str(lod) for lod in range(MAX_NUM_LODS)]


class ImportBackend:

    def __init__(self,
                 filepath,
                 texname,
                 import_all_lods=False,
                 use_facetex=False,
                 import_bsp=False):
        self.filepath = filepath
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

    def make_loops(self, edges):
        """Generates loops for vertices and edges in order to make faces."""
        used_verts = []
        used_edges = []
        for e in edges:
            if e.index not in used_edges:
                if e.vertices[0] not in used_verts:
                    used_edges.append(e.index)
                    used_verts.append(e.vertices[0])
                    yield (e.index, e.vertices[0])
                elif e.vertices[1] not in used_verts:
                    used_edges.append(e.index)
                    used_verts.append(e.vertices[1])
                    yield (e.index, e.vertices[1])
                else:
                    print("Potential problem encountered!!",
                          "used_verts: {!r}, used_edges: {!r}".format(
                              used_verts, used_edges
                          ))
                    raise StopIteration()

    def edges_from_verts(self, verts):
        """Generates vertex reference tuples for edges."""
        if all(map(lambda e: isinstance(e, int), verts)):
            for idx in range(len(verts)):
                first_idx = verts[idx]
                next_idx = verts[idx + 1]
                if next_idx >= len(verts): next_idx = 0
                yield {first_idx, next_idx}
        else:
            raise TypeError("{0!r} ain't vertex references!")

    def to_bl_mesh(self):
        """Take the data and convert it to Blender mesh data."""
        if (len(self._verts) > 0 and
                len(self._norms) > 0 and
                len(self._fvrts) > 0 and
                len(self._faces) > 0 and
                self._name != ""):
            bl_mesh = bpy.data.meshes.new(self._name)
            bl_mesh.vertices.add(len(self._verts))
            for idx, v in enumerate(self._verts):
                bl_mesh.vertices[idx].co = v
            face_edges = []
            edge_refs = []
            for fidx, f in enumerate(self._faces):
                # used_fvrts = []
                cur_edge_verts = []
                for fvrt_ofs in range(f[4]):  # Number of vertices on the face
                    cur_fvrt = f[3] + fvrt_ofs  # f[3] is index of first FVRT
                    cur_edge_verts.append(self._fvrts[cur_fvrt][0])
                    bl_mesh.vertices[self._fvrts[cur_fvrt][0]].normal = (
                        self._vtnms[self._fvrts[cur_fvrt][1]])
                    # used_fvrts.append(f[3] + fvrt_ofs)
                edge_refs.append([])
                for ed in self.edges_from_verts(cur_edge_verts):
                    if ed not in face_edges:
                        eidx = len(face_edges)
                        face_edges.append(tuple(ed))
                    else:
                        eidx = face_edges.index(ed)
                    edge_refs[fidx].append(eidx)
                if f[2] not in self.texdict.keys():
                    mat_name = self.texname.format(len(self.texdict) + 1)
                    self.texdict[f[2]] = (len(bl_mesh.materials), mat_name)
                    texture_available = False

                    if fexists("../mat/{0:0>8d}.mat".format(f[2])):
                        # Read MAT file
                        # TODO: implement reading and parsing of MAT files.
                        raise NotImplementedError("Cannot read MAT files.")
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
            cur_loop_vert = 0
            for fidx, f in enumerate(self._faces):
                bl_mesh.polygons[fidx].material_index = self.texdict[f[2]][0]
                bl_mesh.polygons[fidx].normal = self._vtnms[f[0]]
                f_verts = [fvrt[0] for fvrt in self._fvrts[f[3]:f[3] + f[4]]]
                f_edges = edge_refs[fidx]
                print("f_verts: {!r}, f_edges: {!r}".format(f_verts, f_edges))
                bl_mesh.polygons[fidx].vertices = f_verts
                for lp in self.make_loops(f_edges):
                    bl_mesh.loops.add(1)
                    bl_mesh.loops.edge_index, bl_mesh.loops.vertex_index = lp
                bl_mesh.polygons[fidx].loop_start = cur_loop_vert
                bl_mesh.polygons[fidx].loop_total = f[4]
                cur_loop_vert += f[4]
        return bl_mesh


class Hardpoint:

    def __init__(self, pos_data, name):
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
        # TODO: Set rotation of object
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
            length = (struct.unpack(">i", self.iff_file.read(4))[0]) - 4
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

    def read_mesh_data(self, mesh_form):
        texdict = {}

        mjrf_bytes_read = 0
        # Read all LODs
        while mjrf_bytes_read < mesh_form["length"]:
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
                mjrf_bytes_read += 8 + geom_data["length"]
                # Ignore RADI
                if geom_data["name"] == geom_chunks[0]:  # NAME
                    name_str = self.read_cstring(geom_data, 0)
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
                    "mjr form length:", mesh_form["length"],
                    "mjr form read:", mjrf_bytes_read
                )
            bl_ob = bpy.data.objects.new(
                LOD_NAMES[self.cur_lod],
                lodm.to_bl_mesh())
            bpy.context.scene.objects.link(bl_ob)

    def read_hard_data(self):
        mjrf_bytes_read = 0
        while mjrf_bytes_read < major_form["length"]:
            hardpt_chunk = self.read_data()
            mjrf_bytes_read += hardpt_chunk["length"]
            hardpt_data = struct.unpack(
                "<ffffffffffff",
                hardpt_chunk["data"]
            )
            hardpt_name_ofs = 48
            hardpt_name = self.read_cstring(hardpt_chunk, hardpt_name_ofs)
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
            cstring.append(the_byte)
            ofs += 1
        del cstring[-1]
        return cstring.decode("iso-8859-1")

    def load(self):
        self.iff_file = open(self.filepath, "rb")
        root_form = self.read_data()
        if root_form["type"] == "form" and root_form["name"] == b"DETA":
            mjrfs_read = 0
            while mjrfs_read < root_form["length"]:
                major_form = self.read_data()
                mjrfs_read += major_form["length"]
                print("Reading major form:", major_form["name"])
                if major_form["name"] == b"RANG":
                    pass  # RANG data is useless to Blender.
                elif major_form["name"] == b"MESH":
                    self.read_mesh_data()
                elif major_form["name"] == b"HARD":
                    self.read_hard_data()
                elif major_form["name"] == b"COLL":
                    self.read_coll_data()
                elif major_form["name"] == b"FAR ":
                    pass  # FAR data is useless to Blender.
        else:
            raise TypeError("This file isn't a mesh!")

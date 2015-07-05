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
from mathutils import Vector
from itertools import starmap
from collections import OrderedDict

LOD_NAMES = ["detail-" + str(lod) for lod in range(MAX_NUM_LODS)]


class ImportBackend:

    def __init__(self,
                 filepath,
                 texname,
                 import_all_lods=False,
                 use_facetex=False,
                 import_bsp=False):
        self.filepath = filepath
        self.texname = texname
        self.import_all_lods = import_all_lods
        self.use_facetex = use_facetex
        self.import_bsp = import_bsp

        if self.texname.isspace():
            self.texname = "Untitled"


class LODMesh:

    def __init__(self):
        self._verts = []
        self._norms = []
        self._fvrts = []
        self._faces = []
        self._name = ""

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
            self._fvrts.append(vert)
        else:
            raise TypeError("{0!r} ain't no FVRT!".format(fvrt))

    def add_face(self, face):
        """Add FACE data to this mesh."""
        def validate_face(idx, face_el):
            if idx != 1:
                return isinstance(face_el, int)
            else:
                return isinstance(face_el, float)

        if len(face) == 7 and all(starmap(validate_face, enumerate(face))):
            self._faces.append(face)
        else:
            raise TypeError("{0!r} ain't no FACE!".format(face))

    def set_name(self, name):
        """Set the name of this mesh."""
        self._name = name.strip()

    def set_cntr(self, cntr):
        """Set the center point for this mesh."""
        if len(cntr) == 3 and all(map(lambda e: type(e) == float)):
            self._cntr = cntr
        else:
            raise TypeError("{0!r} ain't no CNTR!".format(cntr))

    def make_loops(self, verts, edges):
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
            textures = dict()
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
            bl_mesh.edges.add(len(face_edges))
            for eidx, ed in enumerate(face_edges):
                bl_mesh.edges[eidx].vertices = ed
            bl_mesh.polygons.add(len(self._faces))
            num_loop_verts = 0
            for fidx, f in enumerate(self._faces):
                bl_mesh.polygons[fidx].normal = self._vtnms[f[0]]
                f_verts = (fvrt[0] for fvrt in self._fvrts[f[3]:f[3] + f[4]])
                f_edges = edge_refs[fidx]
                print("f_verts: {!r}, f_edges: {!r}".format(f_verts, f_edges))
                bl_mesh.polygons[fidx].vertices = f_verts
                for lp in self.make_loops(f_verts, f_edges):
                    bl_mesh.loops.add(1)
                    bl_mesh.loops.edge_index = lp[0]
                    bl_mesh.loops.vertex_index = lp[1]
                bl_mesh.polygons[fidx].loop_start = num_loop_verts
                bl_mesh.polygons[fidx].loop_total = f[4]
                num_loop_verts += f[4]
        return bl_mesh


class IFFImporter(ImportBackend):

    iff_heads = [b"FORM", b"CAT ", b"LIST"]

    def skip_data(self, file):
        orig_pos = file.tell()
        head = file.read(4)
        if head in self.iff_heads:
            file.read(8)
        elif head.isalnum() or head == b"FAR ":
            length = struct.unpack(">i", file.read(4))[0]
            file.read(length)
        else:
            raise TypeError("This file is not a valid IFF file!")
        return None

    def read_data(self, file):
        orig_pos = file.tell()
        head = file.read(4)
        if head in self.iff_heads:
            length = struct.unpack(">i", file.read(4))[0] - 4
            name = file.read(4)
            return {
                "type": "form",
                "length": length,
                "name": name,
                "offset": orig_pos
            }
        elif head.isalnum() or head == b"FAR ":
            name = file.read(4)
            length = struct.unpack(">i", file.read(4))[0]
            data = file.read(length)
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

    def load(self):
        lods = {}
        textures = dict()

        iff_file = open(self.filepath, "r")
        root_form = self.read_iff_data(iff_file)
        if root_form["type"] == "form" and root_form["name"] == b"DETA":
            self.skip_data(iff_file)
            lods_form = self.read_data(iff_file)
            lods_bytes_read = 0
            if lods_form["name"] == b"MESH":
                # Read all LODs
                while lods_bytes_read < lods_form["length"]:
                    lod_form = self.read_data(iff_file)
                    lods_bytes_read += 12
                    lod_lev = lod_form["name"].decode("iso-8859-1").lstrip("0")
                    if lod_lev == "": self.cur_lod = 0
                    else: self.cur_lod = int(lod_lev)

                    lodm = LODMesh()

                    self.skip_data(iff_file)  # Skip a MESH form
                    lods_bytes_read += 12
                    geom = self.read_data(iff_file)
                    lods_bytes_read += 12

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
                        geom_data = self.read_data(iff_file)
                        lods_bytes_read += geom_data["length"]
                        # Ignore RADI
                        if geom_data["name"] == geom_chunks[0]:  # NAME
                            name_str = bytearray()
                            the_byte = 1
                            while the_byte != 0:
                                the_byte = iff_file.read(1)
                                name_str.append(the_byte)
                            del name_str[-1]
                            lodm.set_name(name_str.decode("iso-8859-1"))
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
                                    "<iiff",
                                    geom_data["data"],
                                    fvrt_idx * 16
                                ))
                                fvrt_idx += 1
                        elif geom_data["name"] == geom_chunks[4]:  # FACE
                            face_idx = 0
                            while face_idx * 28 < geom_data["length"]:
                                # Multiply by 28 to skip "unknown2" value
                                lodm.add_face(struct.unpack_from(
                                    "<ifiiii",
                                    geom_data["data"],
                                    face_idx * 28
                                ))
                                face_idx += 1
                        elif geom_data["name"] == geom_chunks[5]:  # CNTR
                            lodm.set_cntr(struct.unpack(
                                "<fff", geom_data["data"]
                            ))
                        geom_chunks_read += 1
        else:
            raise TypeError("This file isn't a mesh!")

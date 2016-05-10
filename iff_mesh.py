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

# Classes for WCP/SO IFF Meshes
from . import iff
import warnings


def colour_texnum(colour):
    import struct

    # Make Blender mathutils import optional
    try:
        # Using Blender imports
        import mathutils
        if not isinstance(colour, mathutils.Color):
            raise TypeError("The colour you want to convert must be a valid "
                            "Blender colour!")
    except ImportError:
        # Not using Blender imports
        if not isinstance(colour, list) or not isinstance(colour, tuple):
            raise TypeError("The colour you want to convert must be a valid "
                            "colour!")
    for cc in colour:
        if not isinstance(cc, float):
            raise TypeError("The colour you want to convert must be a valid "
                            "Blender colour!")

    def clamp_byte(x):
        if x <= 0: return 0
        elif x >= 256: return 255
        else: return x

    clrbytes = [round(cc * 256) for cc in colour]
    clrbytes = map(clamp_byte, clrbytes)
    tnbytes = struct.pack("<BBBB", 0x7F, *clrbytes)
    tnint = struct.unpack(">I", tnbytes)[0]
    return tnint


class Collider:
    # Collision sphere or BSP tree

    COLLIDER_TYPES = ["sphere", "bsp", "bsp+region"]

    def __init__(self, col_type, *data):
        if col_type not in self.COLLIDER_TYPES:
            raise ValueError("Invalid collider type %s!" % col_type)

        if not isinstance(data[0], Sphere):
            raise TypeError("A collider must have a boundary sphere!")

        # if ((col_type == "bsp" or col_type == "bsp+region") and
        #         not isinstance(data[1], bsp.BSPTree)):
        #     raise TypeError("Collider data for a BSP collider must have a "
        #                     "sphere and a BSP tree!")
        #
        # if (col_type == "bsp+region" and
        #         not isinstance(data[2], bsp.Blockmap)):
        #     raise TypeError("Collider data for a BSP collider must have a "
        #                     "sphere and a BSP tree!")

        if col_type == "bsp" or col_type == "bsp+region":
            raise TypeError("BSP trees are not yet supported!")

        self.col_type = col_type
        self.data = data

    def to_coll_form(self):
        coll_form = iff.IffForm("COLL")
        sphr_chnk = self.data[0].to_collsphr_chunk()
        coll_form.add_member(sphr_chnk)

        if self.col_type == "bsp":
            if self.data[1] is not None:
                extn_form = iff.IffForm("EXTN")
                coll_form.add_member(extn_form)
            else:
                raise TypeError("data[1] must be a BSP tree!")

        return coll_form

    def __str__(self):
        strr = "{} collider: (".format(self.col_type.capitalize())
        for didx in range(len(self.data)):
            strr += "{!s}".format(self.data[didx])
            if didx < len(self.data) - 1: strr += ", "
        strr += ")"
        return strr


class Sphere:
    # CNTR/RADI chunks for each LOD

    def __init__(self, x, y, z, r):
        if not isinstance(x, float):
            raise TypeError("X Coordinate must be a float!")
        if not isinstance(y, float):
            raise TypeError("Y Coordinate must be a float!")
        if not isinstance(z, float):
            raise TypeError("Z Coordinate must be a float!")
        if not isinstance(r, float):
            raise TypeError("Radius must be a float!")

        self.x = x
        self.y = y
        self.z = z
        self.r = r

    def to_tuple(self):
        return (self.x, self.y, self.z, self.r)

    def to_cntr_chunk(self):
        cntr_chunk = iff.IffChunk("CNTR")
        cntr_chunk.add_member(self.x)
        cntr_chunk.add_member(self.z)
        cntr_chunk.add_member(self.y)
        return cntr_chunk

    def to_radi_chunk(self):
        radi_chunk = iff.IffChunk("RADI")
        radi_chunk.add_member(self.r)
        return radi_chunk

    def to_collsphr_chunk(self):
        collsphr_chunk = iff.IffChunk("SPHR")
        collsphr_chunk.add_member(self.x)
        collsphr_chunk.add_member(self.z)
        collsphr_chunk.add_member(self.y)
        collsphr_chunk.add_member(self.r)
        return collsphr_chunk

    def to_chunks(self):
        return self.to_cntr_chunk(), self.to_radi_chunk()

    def to_bl_obj(self):
        import bpy
        bl_obj = bpy.data.objects.new("cntradi", None)
        bl_obj.empty_draw_type = "SPHERE"

        bl_obj.location.x = self.x
        bl_obj.location.y = self.y
        bl_obj.location.z = self.z
        bl_obj.scale = self.r, self.r, self.r

        return bl_obj

    @staticmethod
    def from_chunks(cntr_chunk, radi_chunk):
        import struct

        x, y, z = struct.unpack("<fff", cntr_chunk)
        r = struct.unpack("<f", radi_chunk)[0]

        return Sphere(x, y, z, r)

    def __str__(self):
        return "Sphere ({0.x:.4f}, {0.y:.4f}, {0.z:.4f}:{0.r:.4f})".format(
            self)


class Hardpoint:
    # Hardpoints

    def __init__(self, rot_matrix, location, name):
        # rot_matrix should be a mathutils.Matrix or compatible value
        # location should be a mathutils.Vector or compatible value

        self.rot_matrix = rot_matrix
        self.location = location
        self.name = name

    def to_chunk(self):
        hard_chunk = iff.IffChunk("HARD")
        hard_chunk.add_member(self.rot_matrix[0][0])
        hard_chunk.add_member(self.rot_matrix[0][1])
        hard_chunk.add_member(self.rot_matrix[0][2])
        hard_chunk.add_member(self.location[0])
        hard_chunk.add_member(self.rot_matrix[1][0])
        hard_chunk.add_member(self.rot_matrix[1][1])
        hard_chunk.add_member(self.rot_matrix[1][2])
        hard_chunk.add_member(self.location[1])
        hard_chunk.add_member(self.rot_matrix[2][0])
        hard_chunk.add_member(self.rot_matrix[2][1])
        hard_chunk.add_member(self.rot_matrix[2][2])
        hard_chunk.add_member(self.location[2])
        hard_chunk.add_member(self.name)
        return hard_chunk

    def to_bl_obj(self):
        import bpy
        from mathutils import Matrix
        bl_obj = bpy.data.objects.new("hp-" + self.name, None)
        bl_obj.empty_draw_type = "ARROWS"

        matrix_rot = Matrix(self.rot_matrix).to_4x4()

        # Convert position/rotation from WC
        euler_rot = matrix_rot.to_euler("XYZ")
        euler_rot.y, euler_rot.z = -euler_rot.z, -euler_rot.y
        euler_rot.x *= -1

        matrix_rot = euler_rot.to_matrix().to_4x4()
        matrix_loc = Matrix.Translation((self._x, self._z, self._y))

        bl_obj.matrix_basis = matrix_loc * matrix_rot
        return bl_obj

    @staticmethod
    def from_chunk(cls, chunk_data):
        import struct

        def read_cstring(data, ofs):
            cstring = bytearray()
            while data[ofs] != 0:
                if data[ofs] == 0: break
                cstring.append(data[ofs])
                ofs += 1
            return cstring.decode("ascii")

        hardpt_data = struct.unpack_from("<ffffffffffff", chunk_data, 0)

        hardpt_rot = (
            (hardpt_data[0], hardpt_data[1], hardpt_data[2]),
            (hardpt_data[4], hardpt_data[5], hardpt_data[6]),
            (hardpt_data[8], hardpt_data[9], hardpt_data[10])
        )

        hardpt_loc = (hardpt_data[3], hardpt_data[7], hardpt_data[11])

        hardpt_name_ofs = 48
        hardpt_name = read_cstring(chunk_data, hardpt_name_ofs)

        return Hardpoint(hardpt_rot, hardpt_loc, hardpt_name)

    def __str__(self):
        return "Hardpoint \"{0}\" ({1.x:.4f}, {1.y:.4f}, {1.z:.4f})".format(
            self.name, self.location
        )


class MeshLODForm(iff.IffForm):
    def __init__(self, LOD, version=12):
        # No call to superclass constructor because we set the same values
        # in this constructor
        self._name = "{!s:0>4}".format(LOD)
        self._mesh_form = iff.IffForm("MESH")
        self._geom_form = iff.IffForm("{!s:0>4}".format(version))
        self._name_chunk = iff.IffChunk("NAME")
        self._vert_chunk = iff.IffChunk("VERT")
        self._vtnm_chunk = iff.IffChunk("VTNM")
        self._fvrt_chunk = iff.IffChunk("FVRT")
        self._face_chunk = iff.IffChunk("FACE")
        self._cntr_chunk = iff.IffChunk("CNTR")
        self._radi_chunk = iff.IffChunk("RADI")
        self._geom_form.add_member(self._name_chunk)
        self._geom_form.add_member(self._vert_chunk)
        self._geom_form.add_member(self._vtnm_chunk)
        self._geom_form.add_member(self._fvrt_chunk)
        self._geom_form.add_member(self._face_chunk)
        self._geom_form.add_member(self._cntr_chunk)
        self._geom_form.add_member(self._radi_chunk)
        self._mesh_form.add_member(self._geom_form)
        self._members = [self._mesh_form]

    def set_name(self, name):
        # Check data types before adding to respective chunks
        if self._name_chunk.has_members():
            self._name_chunk.clear_members()
        if isinstance(name, str):
            self._name_chunk.add_member(name)
        else:
            raise TypeError("Name of this mesh LOD must be a string!")

    def add_vertex(self, vx, vy, vz):
        if not (isinstance(vx, float) and
                isinstance(vy, float) and
                isinstance(vz, float)):
            raise TypeError("The vertex coordinates must be floating point"
                            " values!")

        self._vert_chunk.add_member(vx)
        self._vert_chunk.add_member(vy)
        self._vert_chunk.add_member(vz)

    def add_normal(self, nx, ny, nz):
        if not (isinstance(nx, float) and
                isinstance(ny, float) and
                isinstance(nz, float)):
            raise TypeError("The normal vector must be floating point values!")

        self._vtnm_chunk.add_member(nx)
        self._vtnm_chunk.add_member(ny)
        self._vtnm_chunk.add_member(nz)

    def add_fvrt(self, vert_idx, vtnm_idx, uv_x, uv_y):
        if (not(isinstance(vert_idx, int) and
                isinstance(vtnm_idx, int))):
            raise TypeError("The vertex and vertex normal indices must"
                            " be integers!")
        if (not(isinstance(uv_x, float) and
                isinstance(uv_y, float))):
            raise TypeError("The UV coordinates must be floating point"
                            " values!")

        self._fvrt_chunk.add_member(vert_idx)
        self._fvrt_chunk.add_member(vtnm_idx)
        self._fvrt_chunk.add_member(uv_x)
        self._fvrt_chunk.add_member(uv_y)

    def add_face(self, vtnm_idx, dplane, texnum,
                 fvrt_idx, num_verts, light_flags, alt_mat=0x7F0096FF):
        if not isinstance(vtnm_idx, int):
            raise TypeError("Vertex normal index must be an integer!")
        if not isinstance(dplane, float):
            raise TypeError("D-Plane value must be a floating point number!")
        if not isinstance(texnum, int):
            raise TypeError("Texture number must be an integer!")
        if not isinstance(fvrt_idx, int):
            raise TypeError("First FVRT index must be an integer!")
        if not isinstance(num_verts, int):
            raise TypeError("Number of vertices must be an integer!")
        if not isinstance(light_flags, int):
            raise TypeError("Lighting wordflag must be an integer!")
        if not isinstance(alt_mat, int):
            raise TypeError("Alternate MAT must be an integer!")

        self._face_chunk.add_member(vtnm_idx)  # Face normal
        self._face_chunk.add_member(dplane)  # D-Plane
        self._face_chunk.add_member(texnum)  # Texture number
        self._face_chunk.add_member(fvrt_idx)  # Index of face's first FVRT
        self._face_chunk.add_member(num_verts)  # Number of vertices
        self._face_chunk.add_member(light_flags)  # Lighting flags
        self._face_chunk.add_member(alt_mat)  # Unknown (alternate MAT?)

    def set_center(self, cx, cy, cz):
        warnings.warn("set_center is deprecated! Use set_cntradi instead.",
                      DeprecationWarning)

        if self._cntr_chunk.has_members():
            self._cntr_chunk.clear_members()
        if (isinstance(cx, float) and
                isinstance(cy, float) and
                isinstance(cz, float)):
            self._cntr_chunk.add_member(cx)
            self._cntr_chunk.add_member(cy)
            self._cntr_chunk.add_member(cz)
        else:
            raise TypeError("Center coordinates must be floating point"
                            " values!")

    def set_radius(self, radius):
        warnings.warn("set_radius is deprecated! Use set_cntradi instead.",
                      DeprecationWarning)

        if self._radi_chunk.has_members():
            self._radi_chunk.clear_members()
        if isinstance(radius, float):
            self._radi_chunk.add_member(radius)
        else:
            raise TypeError("Radius must be a floating point value!")

    def set_cntradi(self, sphere):

        if not isinstance(sphere, Sphere):
            raise TypeError("You must use a valid Sphere object to set the "
                            "center location and radius for this LOD.")

        self._cntr_chunk.clear_members()
        self._radi_chunk.clear_members()

        self._cntr_chunk.add_member(sphere.x)
        self._cntr_chunk.add_member(sphere.y)
        self._cntr_chunk.add_member(sphere.z)
        self._radi_chunk.add_member(sphere.r)

    # Do not use! These methods are only here for backwards compatibility
    def get_name_chunk(self):
        warnings.warn("get_name_chunk is deprecated!", DeprecationWarning)
        return self._name_chunk

    def get_vert_chunk(self):
        warnings.warn("get_vert_chunk is deprecated!", DeprecationWarning)
        return self._vert_chunk

    def get_vtnm_chunk(self):
        warnings.warn("get_vtnm_chunk is deprecated!", DeprecationWarning)
        return self._vtnm_chunk

    def get_fvrt_chunk(self):
        warnings.warn("get_fvrt_chunk is deprecated!", DeprecationWarning)
        return self._fvrt_chunk

    def get_face_chunk(self):
        warnings.warn("get_face_chunk is deprecated!", DeprecationWarning)
        return self._face_chunk

    def get_cntr_chunk(self):
        warnings.warn("get_cntr_chunk is deprecated!", DeprecationWarning)
        return self._cntr_chunk

    def get_radi_chunk(self):
        warnings.warn("get_radi_chunk is deprecated!", DeprecationWarning)
        return self._radi_chunk


class MeshIff(iff.IffFile):
    # Manages the IFF data for a VISION engine 3D model.

    def __init__(self, filename, include_far_chunk, dranges):

        if not isinstance(include_far_chunk, bool):
            raise TypeError("include_far_chunk must be a boolean value!")

        if isinstance(dranges, list) or isinstance(dranges, tuple):
            for drange in dranges:
                if not isinstance(drange, float):
                    raise TypeError("Each LOD range must be a float!")
        else:
            raise TypeError("dranges must be a list or tuple!")

        # Initialize an empty mesh IFF file, initialize data structures, etc.
        super().__init__("DETA", filename)

        self._mrang = iff.IffChunk("RANG", dranges)
        self.root_form.add_member(self._mrang)

        self._mmeshes = iff.IffForm("MESH")
        self.root_form.add_member(self._mmeshes)

        self._mhard = iff.IffForm("HARD")
        self.root_form.add_member(self._mhard)

        self._mcoll = iff.IffForm("COLL")
        self.root_form.add_member(self._mcoll)

        if include_far_chunk:
            self._mfar = iff.IffChunk("FAR ", [float(0), float(900000)])
            self.root_form.add_member(self._mfar)

    def make_coll_sphr(self, X, Y, Z, radius):
        warnings.warn("make_coll_sphr is deprecated! "
                      "Use set_collider instead.", DeprecationWarning)

        if self._mcoll.has_members():
            for mem in range(self._mcoll.get_num_members()):
                self._mcoll.remove_member(mem)

        _mcollsphr = iff.IffChunk("SPHR")
        _mcollsphr.add_member(X)
        _mcollsphr.add_member(Y)
        _mcollsphr.add_member(Z)
        _mcollsphr.add_member(radius)
        self._mcoll.add_member(_mcollsphr)

    def set_collider(self, collider):
        if not isinstance(collider, Collider):
            raise TypeError("collider must be a valid Collider in order to "
                            "use it for this model!")

        self._mcoll = collider.to_coll_form()

    def add_hardpt(self, x, y, z, rot_matrix, name):
        hardpt = iff.IffChunk("HARD")
        hardpt.add_member(rot_matrix[0][0])
        hardpt.add_member(rot_matrix[0][1])
        hardpt.add_member(rot_matrix[0][2])
        hardpt.add_member(x)
        hardpt.add_member(rot_matrix[1][0])
        hardpt.add_member(rot_matrix[1][1])
        hardpt.add_member(rot_matrix[1][2])
        hardpt.add_member(y)
        hardpt.add_member(rot_matrix[2][0])
        hardpt.add_member(rot_matrix[2][1])
        hardpt.add_member(rot_matrix[2][2])
        hardpt.add_member(z)
        hardpt.add_member(name)
        self._mhard.add_member(hardpt)

    def remove_hardpt(self, hp_idx):
        self._mhard.remove_member(hp_idx)

    def remove_hardpts(self):
        self._mhard.clear_members(mem)

    def add_lod(self, lod):
        if isinstance(lod, MeshLODForm):
            self._mmeshes.add_member(lod)

    def set_dranges(self, dranges):
        if isinstance(dranges, list) or isinstance(dranges, tuple):
            for drange in dranges:
                if not isinstance(drange, float):
                    raise TypeError("Each LOD range must be a float!")
        else:
            raise TypeError("dranges must be a list or tuple!")

        self._mrang.clear_members()
        for drange in dranges:
            self._mrang.add_member(drange)

    def get_meshes_form(self):
        warnings.warn("get_meshes_form is deprecated!", DeprecationWarning)
        return self._mmeshes

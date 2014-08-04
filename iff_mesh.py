import iff
import warnings


class MeshLODForm(iff.IffForm):
    def __init__(self, LOD, version=12):
        self._name = "{!s:0>4}".format(LOD)
        self._mesh_form = iff.IffForm("MESH")
        self._geom_form = iff.IffForm("{!s:0>4}".format(version))
        self.name_chunk = iff.IffChunk("NAME")
        self.vert_chunk = iff.IffChunk("VERT")
        self.vtnm_chunk = iff.IffChunk("VTNM")
        self.fvrt_chunk = iff.IffChunk("FVRT")
        self.face_chunk = iff.IffChunk("FACE")
        self.cntr_chunk = iff.IffChunk("CNTR")
        self.radi_chunk = iff.IffChunk("RADI")
        self._geom_form.add_member(self.name_chunk)
        self._geom_form.add_member(self.vert_chunk)
        self._geom_form.add_member(self.vtnm_chunk)
        self._geom_form.add_member(self.fvrt_chunk)
        self._geom_form.add_member(self.face_chunk)
        self._geom_form.add_member(self.cntr_chunk)
        self._geom_form.add_member(self.radi_chunk)
        self._mesh_form.add_member(self._geom_form)
        self._members = [self._mesh_form]

    def set_name(self, name):
        if name_chunk.has_members():
            name_chunk.clear_members()
        if isinstance(name, str):
            name_chunk.add_member(name)
        else:
            raise TypeError("Name of this mesh LOD must be a string!")

    def add_vertex(self, vx, vy, vz):
        # Check data types before adding to respective chunks
        if (isinstance(vx, float) and
                isinstance(vy, float) and
                isinstance(vz, float)):
            vert_chunk.add_member(vx)
            vert_chunk.add_member(vy)
            vert_chunk.add_member(vz)
        else:
            raise TypeError("The vertex coordinates must be floating point"
                            " values!")

    def add_normal(self, nx, ny, nz):
        # Check data types before adding to respective chunks
        if (isinstance(nx, float) and
                isinstance(ny, float) and
                isinstance(nz, float)):
            vtnm_chunk.add_member(nx)
            vtnm_chunk.add_member(ny)
            vtnm_chunk.add_member(nz)
        else:
            raise TypeError("The normal vector must be floating point"
                            " values!")

    def add_fvrt(self, vert_idx, vtnm_idx, uv_x, uv_y):
        if (not(isinstance(vert_idx, int) and
                isinstance(vtnm_idx, int))):
            raise TypeError("The vertex and vertex normal indices must"
                            " be integers!")
        if (not(isinstance(uv_x, float) and
                isinstance(uv_y, float))):
            raise TypeError("The UV coordinates must be floating point"
                            " values!")
        # Both data types have been checked, so
        # we know we can safely add them to the chunk
        fvrt_chunk.add_member(vert_idx)
        fvrt_chunk.add_member(vtnm_idx)
        fvrt_chunk.add_member(uv_x)
        fvrt_chunk.add_member(uv_y)

    def add_face(self, vtnm_idx, dplane, texnum,
                 fvrt_idx, num_verts, light_flags):
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
        face_chunk.add_member(vtnm_idx)  # Face normal
        face_chunk.add_member(dplane)  # D-Plane
        face_chunk.add_member(texnum)  # Texture number
        face_chunk.add_member(fvrt_idx)  # Index of face's first FVRT
        face_chunk.add_member(num_verts)  # Number of vertices
        face_chunk.add_member(light_flags)  # Lighting flags
        face_chunk.add_member(0x7F0096FF)  # Unknown

    def set_center(self, cx, cy, cz):
        if cntr_chunk.has_members():
            cntr_chunk.clear_members()
        if (isinstance(cx, float) and
                isinstance(cy, float) and
                isinstance(cz, float)):
            cntr_chunk.add_member(cx)
            cntr_chunk.add_member(cy)
            cntr_chunk.add_member(cz)
        else:
            raise TypeError("Center coordinates must be floating point"
                            " values!")

    def set_radius(self, radius):
        if radi_chunk.has_members():
            radi_chunk.clear_members()
        if isinstance(radius, float):
            radi_chunk.add_member(radius)
        else:
            raise TypeError("Radius must be a floating point value!")


    # Do not use! These methods are only here for backwards compatibility
    def get_name_chunk(self):
        warnings.warn("get_name_chunk is deprecated!", DeprecationWarning)
        return self.name_chunk

    def get_vert_chunk(self):
        warnings.warn("get_vert_chunk is deprecated!", DeprecationWarning)
        return self.vert_chunk

    def get_vtnm_chunk(self):
        warnings.warn("get_vtnm_chunk is deprecated!", DeprecationWarning)
        return self.vtnm_chunk

    def get_fvrt_chunk(self):
        warnings.warn("get_fvrt_chunk is deprecated!", DeprecationWarning)
        return self.fvrt_chunk

    def get_face_chunk(self):
        warnings.warn("get_face_chunk is deprecated!", DeprecationWarning)
        return self.face_chunk

    def get_cntr_chunk(self):
        warnings.warn("get_cntr_chunk is deprecated!", DeprecationWarning)
        return self.cntr_chunk

    def get_radi_chunk(self):
        warnings.warn("get_radi_chunk is deprecated!", DeprecationWarning)
        return self.radi_chunk


class MeshIff(iff.IffFile):
    def __init__(self, filename):
        # Initialize an empty mesh IFF file, initialize data structures, etc.
        super().__init__("DETA", filename)

        self._mrang = iff.IffChunk("RANG", [float(0), float(400), float(800)])
        self.root_form.add_member(self._mrang)

        self.mmeshes = iff.IffForm("MESH")
        self.root_form.add_member(self.mmeshes)

        self._mhard = iff.IffForm("HARD")
        self.root_form.add_member(self._mhard)

        self._mcoll = iff.IffForm("COLL")
        self.root_form.add_member(self._mcoll)

        self._mfar = iff.IffChunk("FAR ", [float(0), float(900000)])
        self.root_form.add_member(self._mfar)

    def make_coll_sphr(self, X, Y, Z, radius):
        if self._mcoll.has_members():
            for mem in range(self._mcoll.get_num_members()):
                self._mcoll.remove_member(mem)

        _mcollsphr = iff.IffChunk("SPHR")
        _mcollsphr.add_member(X)
        _mcollsphr.add_member(Y)
        _mcollsphr.add_member(Z)
        _mcollsphr.add_member(radius)
        self._mcoll.add_member(_mcollsphr)

    def make_coll_tree(self):
        return NotImplemented

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
        for mem in range(self.root_form.get_num_members()):
            self._mhard.remove_member(mem)

    def add_lod(self, lod):
        if isinstance(lod, MeshLODForm):
            self.mmeshes.add_member(lod)

    def get_meshes_form(self):
        warnings.warn("get_meshes_form is deprecated!", DeprecationWarning)
        return self.mmeshes

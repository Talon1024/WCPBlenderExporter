import iff


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

    def get_name_chunk(self):
        return self.name_chunk

    def get_vert_chunk(self):
        return self.vert_chunk

    def get_vtnm_chunk(self):
        return self.vtnm_chunk

    def get_fvrt_chunk(self):
        return self.fvrt_chunk

    def get_face_chunk(self):
        return self.face_chunk

    def get_cntr_chunk(self):
        return self.cntr_chunk

    def get_radi_chunk(self):
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

        self.mcoll = iff.IffForm("COLL")
        self.root_form.add_member(self.mcoll)

        self._mfar = iff.IffChunk("FAR ", [float(0), float(900000)])
        self.root_form.add_member(self._mfar)

    def make_coll_sphr(self, X, Y, Z, radius):
        if self.mcoll.has_members():
            for mem in range(self.mcoll.get_num_members()):
                self.mcoll.remove_member(mem)

        _mcollsphr = iff.IffChunk("SPHR")
        _mcollsphr.add_member(X)
        _mcollsphr.add_member(Y)
        _mcollsphr.add_member(Z)
        _mcollsphr.add_member(radius)
        self.mcoll.add_member(_mcollsphr)

    def make_coll_tree(self):
        return NotImplemented

    def get_meshes_form(self):
        return self.mmeshes

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

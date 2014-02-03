#Classes for IFF data structures
import struct
import io


class IffForm:
    # A FORM is an IFF data structure that can hold CHUNKs or other FORMs
    def __init__(self, name, members=[]):
        if len(name) == 4:  # The _name of the FORM must be 4 letters long
            self._name = name
        elif len(name) > 4:
            self._name = name[4:]
        elif len(name) < 4:
            self._name = name.ljust(4)
        # Make a slice copy of the member list so that every FORM can have
        # different members. If this is not done, all FORM objects will have
        # the same members
        self._members = members[:]

    def is_member_valid(self, member):
        if (isinstance(member, IffForm) or
                isinstance(member, IffChunk)):
            return True
        else:
            return False

    def add_member(self, memberToAdd):
        """Add a member to this FORM

        Only CHUNKs or other FORMs may be added to a FORM
        """
        # Only add a member if it is a CHUNK or a FORM
        if self.is_member_valid(memberToAdd):
            self._members.append(memberToAdd)
        else:
            raise TypeError

    def insert_member(self, memberToAdd, pos):
        if self.is_member_valid(memberToAdd):
            self._members.insert(pos, memberToAdd)
        else:
            raise TypeError

    def remove_member(self, memberToRemove):
        """Remove a member from this FORM"""
        self._members.remove(memberToRemove)

    def to_xmf(self):
        """Convert this FORM to an XMF (IFF Source) string"""
        xmfString = io.StringIO()
        xmfString.write('\nFORM "' + self._name + '"\n{\n')
        for x in self._members:
            xmfString.write(x.to_xmf())
        xmfString.write("\n}\n")
        return xmfString.getvalue()

    def to_bytes(self):
        iffbytes = bytes()
        for x in self._members:
            iffbytes = iffbytes + x.to_bytes()
        iffbytes = self._name.encode("ascii", "replace") + iffbytes
        formlen = len(iffbytes)
        iffbytes = struct.pack(">l", formlen) + iffbytes
        iffbytes = b"FORM" + iffbytes
        return iffbytes

    def get_num_members(self):
        return len(self._members)

    def has_members(self):
        return len(self._members) > 0


class IffChunk(IffForm):
    #A CHUNK is an IFF data structure that holds binary data,
    #such as integers, floats, or strings.

    def is_member_valid(self, member):
        if (isinstance(member, int) or
                isinstance(member, float) or
                isinstance(member, str)):
            return True
        else:
            return False

    def to_xmf(self):
        """
        Returns an XMF string.
        """
        xmfString = io.StringIO()
        xmfString.write('CHUNK "' + self._name + '"\n{\n')
        for x in self._members:
            if isinstance(x, int):
                xmfString.write("long %i" % x)
            if isinstance(x, float):
                xmfString.write("float %f" % x)
            if isinstance(x, str):
                xmfString.write('cstring "%s"' % x)
            xmfString.write("\n")
        xmfString.write("}")
        return xmfString.getvalue()

    def to_bytes(self):
        iffbytes = bytes()
        for x in self._members:
            if isinstance(x, int):
                iffbytes = iffbytes + struct.pack("<l", x)
            if isinstance(x, float):
                iffbytes = iffbytes + struct.pack("<f", x)
            if isinstance(x, str):
                iffbytes = iffbytes + x.encode("ascii", "replace")
                iffbytes = iffbytes + b"\x00"
                # If the string contains an even number of characters,
                # add an extra 0-byte for padding
                if (len(x) % 2 == 0):
                    iffbytes = iffbytes + b"\x00"
        iffbytes = struct.pack(">l", len(iffbytes)) + iffbytes
        iffbytes = self._name.encode("ascii", "replace") + iffbytes
        return iffbytes


class IffFile:
    def __init__(self, root_form=IffForm("NONE"),
                 filename="untitled"):
        if isinstance(root_form, IffForm):
            self.root_form = root_form
        elif isinstance(root_form, str):
            self.root_form = IffForm(root_form)
        if isinstance(filename, str):
            self.filename = filename

    def to_xmf(self):
        xmfString = 'IFF "' + self.filename + '"\n{'
        xmfString = xmfString + self.root_form.to_xmf()
        xmfString = xmfString + "}\n"
        return xmfString

    def to_bytes(self):
        return self.root_form.to_bytes()

    def set_root_form(self, root_form):
        if isinstance(root_form, IffForm):
            self.root_form = root_form

    def get_root_form(self):
        return self.root_form

    def write_file_xmf(self):
        fname = self.filename + ".xmf"
        try:
            fd = open(fname, "x")
            fd.close()
        except FileExistsError:
            print("File already exists! Overwriting...")
        fd = open(fname, "w")
        fd.write(self.to_xmf())
        fd.close()

    def write_file_bin(self):
        fname = self.filename + ".iff"
        try:
            fd = open(fname, "x")
            fd.close()
        except FileExistsError:
            print("File already exists! Overwriting...")
        fd = open(fname, "wb")
        fd.write(self.to_bytes())
        fd.close()

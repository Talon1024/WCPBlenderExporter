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

# IFF reader class
from os.path import exists as fexists


class IffReader:

    iff_heads = [b"FORM", b"CAT ", b"LIST"]

    def __init__(self, iff_file):
        self.iff_file = open(iff_file, "rb")

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

            # NOTE: This function doesn't read everything inside a form, and
            # if you're counting the number of bytes to determine whether
            # you've read the FORM completely, start the counter at 4!!
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

            # NOTE: The chunk data is contained in the "data" key
        else:
            raise TypeError("Tried to read an invalid IFF file!")
        return None  # Shouldn't be reachable

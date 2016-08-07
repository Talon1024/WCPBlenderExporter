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

# MAT reader
import struct
import array
from . import iff_read


class MATReader:

    def __init__(self, matfpath):
        self.iff_reader = iff_read.IffReader(matfpath)
        self.palette = None  # To be initialized in read_palette
        self.pixels = None  # To be initialized in read_info

    def read_info(self, info_chunk):
        dimensions = struct.unpack_from("<II", info_chunk["data"], 0)
        self.img_width, self.img_height = dimensions
        # Image width * height * 4 channels per pixel (RGB + Alpha)
        self.pixels = array.array(
            'B', [0 for x in range(self.img_width * self.img_height * 4)])

    def read_palette(self, cmap_chunk):
        # Each colour is three bytes (R, G, B)
        self.palette = array.array("B", cmap_chunk["data"])

    def read_pxls(self, pxls_chunk):
        # One byte references a colour in the palette
        for cpxl in range(pxls_chunk["length"]):
            palref = struct.unpack_from(
                "<B", pxls_chunk["data"], cpxl)[0]

            self.pixels[cpxl * 4:cpxl * 4 + 3] = (
                self.palette[palref * 3:palref * 3 + 3])
            # Colour at index 0 is transparent by default.
            self.pixels[cpxl * 4 + 3] = 0 if palref == 0 else 255

    def read_alph(self, alph_chunk):
        # One byte for each pixel. The alpha channel is inverted,
        # so 255 would be fully transparent, and 0 is fully opaque
        for apxl in range(alph_chunk["length"]):
            self.pixels[apxl * 4 + 3] = 255 - (struct.unpack_from(
                "<B", alph_chunk["data"], apxl)[0])

    def read(self):
        root_form = self.iff_reader.read_data()
        if root_form["name"] == b"BITM":
            inner_rform = self.iff_reader.read_data()
            if inner_rform["name"] == b"FRAM":
                inner_rform_read = 4

                while inner_rform_read < inner_rform["length"]:

                    mat_data = self.iff_reader.read_data()
                    if (mat_data["type"] == "chunk" and
                            mat_data["name"] == b"INFO"):
                        self.read_info(mat_data)

                    elif (mat_data["type"] == "form" and
                            mat_data["name"] == b"PAL "):
                        self.read_palette(self.iff_reader.read_data())

                    elif (mat_data["type"] == "chunk" and
                            mat_data["name"] == b"PXLS"):
                        self.read_pxls(mat_data)

                    elif (mat_data["type"] == "chunk" and
                            mat_data["name"] == b"ALPH"):
                        self.read_alph(mat_data)

                    inner_rform_read += mat_data["length"] + 8
            else:
                raise TypeError("Invalid texture! (root form is {})".format(
                                inner_rform["name"]))
        else:
            raise TypeError("Invalid texture! (root form is {})".format(
                            root_form["name"]))

    def flip_y(self):
        # Flip the image vertically, row by row
        img_rows = []

        for rowidx in range(self.img_height):
            # Get each row of pixels, and put them into a list of pixel rows
            cur_row_start = rowidx * self.img_width * 4
            cur_row_end = cur_row_start + self.img_width * 4

            img_rows.append(self.pixels[cur_row_start:cur_row_end])

        self.pixels = array.array("B")

        for row in reversed(img_rows):
            self.pixels.extend(row)

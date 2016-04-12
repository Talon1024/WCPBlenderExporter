#!/usr/bin/env python3
# Query MTLs - a little side project of mine.
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
# -*- coding: utf8 -*-

import argparse
import struct
from os import getcwd
from os.path import abspath
from sys import path
import json
path.append(abspath(getcwd() + "/.."))


class IffMatReader:

    PAL_FMT = "<3B"

    def __init__(self, iff_fname):
        from iff_read import IffReader
        self.iff = IffReader(iff_fname)
        # self.out_mode = out_mode
        self.pal = ''
        self.info = {}
        self.hots = []

    def parse_info_chunk(self, info_chunk):
        return struct.unpack("<3i", info_chunk["data"])

    def parse_hots_chunk(self, hots_chunk):
        return struct.unpack("<2i", hots_chunk["data"])

    def parse_pal_form(self, pal_form):
        pal_read = 4
        pal = ''

        while pal_read < pal_form["length"]:
            pal_chunk = self.iff.read_data()

            if pal_chunk["type"] == 'chunk' and pal_chunk["name"] == b"NAME":
                pal = 'external:{}'.format(self.parse_cstr(pal_chunk["data"]))
            elif pal_chunk["type"] == 'chunk' and pal_chunk["name"] == b"CMAP":
                pass
                # pal = 'embedded:{}'.format(", ".join([
                #     "(r:{0}, g:{1}, b:{2})".format(
                #         struct.unpack_from(self.PAL_FMT, pal_chunk["data"], x)
                #         for x in range(0, pal_chunk["length"], 3)
                #     )
                # ]))

            pal_read += 8 + pal_chunk["length"]

        return pal

    def parse_cstr(self, data, offset=0):
        cstr = bytearray()
        while data[offset] != 0:
            cstr.append(data[offset])
            offset += 1
        return cstr.decode("ascii", "ignore")

    def read(self):
        root_form = self.iff.read_data()

        if root_form["name"] == b"BITM":
            fram_form = self.iff.read_data()

            if fram_form["name"] == b"FRAM":
                fram_read = 4
                while fram_read < fram_form["length"]:
                    mdata = self.iff.read_data()

                    if mdata["type"] == 'chunk' and mdata["name"] == b'INFO':
                        (self.info["width"],
                         self.info["height"],
                         self.info["wrap"]) = self.parse_info_chunk(mdata)
                    elif mdata["type"] == 'chunk' and mdata["name"] == b'HOTS':
                        self.hots = self.parse_hots_chunk(mdata)
                    elif mdata["type"] == 'form' and mdata["name"] == b'PAL ':
                        self.pal = self.parse_pal_form(mdata)
                    elif mdata["type"] == 'chunk' and mdata["name"] == b'PXLS':
                        pass
                    elif mdata["type"] == 'chunk' and mdata["name"] == b'ALPH':
                        pass
                    else:
                        print_iff_data(mdata)

                    fram_read += 8 + mdata["length"]
            else:
                print_iff_data(fram_form)
                raise TypeError("Invalid MAT! (no FRAM form found! "
                                "fram_form is %s)" % fram_form["name"])
        else:
            print_iff_data(root_form)
            raise TypeError("Invalid MAT type! (no BITM form found! "
                            "Root form is: %s)" % root_form["name"])


def print_iff_data(iffthing):
    print("--- IFF data ---")
    print("type:", iffthing["type"])
    print("name:", iffthing["name"])
    print("length:", iffthing["length"])
    print("offset:", iffthing["offset"])
    print("data:", iffthing.get("data", "None"))

if __name__ == '__main__':

    argp = argparse.ArgumentParser(
        description="Get information about a VISION engine MAT texture.")

    argp.add_argument('mat', action='store', nargs='+', metavar='mesh.iff',
                      help="The MAT to query.")

    argp.add_argument('--out-format', action='store', nargs='?',
                      metavar='FORMAT', dest='out_fmt', required=False,
                      default='tty', const='tty', choices=['tty', 'json'],
                      help="The format to output the data in.")

    args = argp.parse_args()

    matfs = getattr(args, 'mat', None)
    out_mode = getattr(args, 'out_fmt', "tty")

    for cur_mat, matf in enumerate(matfs):

        if out_mode == "tty":
            print("--- MAT: %s ---" % matf)

        mat_reader = IffMatReader(matf)
        try:
            mat_reader.read()

            if out_mode == "tty":
                print("--- INFO ---")
                print("Width: %d" % mat_reader.info["width"])
                print("Height: %d" % mat_reader.info["height"])
                print("Wrap mode: %d" % mat_reader.info["wrap"])
                print()
                if len(mat_reader.hots) > 0:
                    print("Hotspot(?): {:d}, {:d}".format(*mat_reader.hots))

                if mat_reader.pal.startswith("external:"):
                    print("External palette: %s" % mat_reader.pal[9:])
        except TypeError as te:
            print(str(te))
        except:
            print("Something happened while attempting to parse %s!" % matf)

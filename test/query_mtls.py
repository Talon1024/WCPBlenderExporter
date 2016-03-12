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
import os.path
from sys import path
import json
path.append(os.path.abspath(getcwd() + "/.."))
from iff_read import IffReader


class IffMeshReader:

    FACE_FMT = "<ifiiiii"

    def __init__(self, iff_fname, out_mode):
        self.iff = IffReader(iff_fname)
        self.out_mode = out_mode
        self.lods = {}

    def parse_rang_chunk(self, rang_data):
        # The RANG chunk is just a bunch of floats
        num_ranges = len(rang_data["data"]) // 4
        ranges = struct.unpack("<" + ("f" * num_ranges), mdata["data"])
        return ranges

    def parse_deta_form(self, deta_form):
        pass

    def parse_mesh_form(self, mesh_form):
        mjrmsh_read = 4

        while mjrmsh_read < mesh_form["length"]:

            lod_form = self.iff.read_data()
            lod_lev = int(lod_form["name"].decode("ascii"))
            self.iff.read_data()
            vers_form = self.iff.read_data()
            mesh_vers = int(vers_form["name"].decode("ascii"))
            mjrmsh_read += 36

            mdat_len = vers_form["length"]
            mdat_read = 4

            self.lods[lod_lev] = {}
            self.lods[lod_lev]["mats"] = []
            self.lods[lod_lev]["altmats"] = []
            self.lods[lod_lev]["name"] = ""
            self.lods[lod_lev]["version"] = mesh_vers
            while mdat_read < mdat_len:
                mdat = self.iff.read_data()

                if mdat["type"] == "chunk":
                    mdat_read += 8 + mdat["length"]
                elif mdat["type"] == "form":
                    mdat_read += 12

                if mdat["name"] == b"NAME":
                    self.lods[lod_lev]["name"] = (
                        self.parse_cstr(mdat["data"], 0))
                elif mdat["name"] == b"FACE":
                    for f in struct.iter_unpack(self.FACE_FMT, mdat["data"]):
                        if f[2] not in self.lods[lod_lev]["mats"]:
                            self.lods[lod_lev]["mats"].append(f[2])
                        if f[6] not in self.lods[lod_lev]["altmats"]:
                            self.lods[lod_lev]["altmats"].append(f[2])

    def parse_cstr(self, data, offset):
        cstr = bytearray()
        while data[offset] != 0:
            cstr.append(data[offset])
            offset += 1
        return cstr.decode("ascii", "ignore")

    def parse_hard_form(self, hard_form):
        pass

    def read(self):
        root_form = self.iff.read_data()
        root_read = 4

        if root_form["name"] == b"DETA":
            self.parse_deta_form(root_form)
        elif root_form["name"] == b"MESH":
            self.parse_mesh_form(root_form)


def print_iff_data(iffthing):
    print("--- IFF data ---")
    print("type:", iffthing["type"])
    print("name:", iffthing["name"])
    print("length:", iffthing["length"])
    print("offset:", iffthing["offset"])
    print("data:", iffthing.get("data", "None"))

if __name__ == '__main__':
    face_struct = "<ifiiiii"

    argp = argparse.ArgumentParser(
        description="Find out what materials a WCP/SO mesh uses.",
        epilog="Info will be displayed on a per-LOD basis")
    argp.add_argument('mesh', action='store', nargs='+', metavar='mesh.iff',
                      help="The IFF mesh to query.")
    argp.add_argument('--for-lod', '-l', action='store', nargs='?', type=int,
                      metavar='LOD', dest='for_lod', required=False,
                      default=None,
                      help="The LOD for which to query material usage.")
    argp.add_argument('--out-format', action='store', nargs='?',
                      metavar='FORMAT', dest='out_fmt', required=False,
                      default='tty', const='tty', choices=['tty', 'json'],
                      help="The format to output the data in.")

    args = argp.parse_args()

    for_lod = getattr(args, 'for_lod', None)
    modelfs = getattr(args, 'mesh', None)
    out_mode = getattr(args, 'out_fmt', "tty")

    if out_mode == "json":
        model_data = []

    for cur_model, modelf in enumerate(modelfs):
        used_mtls = []
        used_altmtls = []

        if out_mode == "tty":
            print("--- Model: %s ---" % modelf)
        elif out_mode == "json":
            model_data.append({"name": modelf})

        model = iff_read.IffReader(modelf)

        mroot = model.read_data()
        bytes_read = 4  # NOTE: See iff_read.py for more info

        while bytes_read < mroot["length"]:
            mdata = model.read_data()
            if mdata["type"] == "chunk":
                bytes_read += mdata["length"] + 8  # data + ID and length
            elif mdata["type"] == "form":
                bytes_read += 12  # Type, length, and name
            # print("mroot length: %d, mdata length: %d, bytes_read: %d" % (
            #     mroot["length"], mdata["length"], bytes_read))
            # print_iff_data(mdata)

            if mdata["type"] == "chunk" and mdata["name"] == b"RANG":
                num_lods = len(mdata["data"]) // 4
                lods = struct.unpack("<" + ("f" * num_lods), mdata["data"])
                if out_mode == "json":
                    model_data[cur_model]["lod_ranges"] = lods
                elif out_mode == "tty":
                    print("LOD Distances:", end=" ")
                    print(*lods, sep=", ")

            if mdata["type"] == "form" and mdata["name"] == b"MESH":
                if out_mode == "json":
                    model_data[cur_model]["lods"] = {}
                mjrmsh_bytes = mdata["length"]
                mjrmsh_bytes_read = 4
                numeric_forms_read = 0
                lod_level = None
                mesh_version = None
                while mjrmsh_bytes_read < mjrmsh_bytes:
                    mmdata = model.read_data()
                    mmname = mmdata["name"].decode("ascii", "replace")
                    # Increment byte counter
                    if mmdata["type"] == "form":
                        mjrmsh_bytes_read += 12
                    elif mmdata["type"] == "chunk":
                        mjrmsh_bytes_read += 8 + mmdata["length"]

                    # Process data
                    # Numeric FORMs (LOD number and version)
                    if mmdata["type"] == "form" and mmname.isnumeric():
                        if numeric_forms_read % 2 == 0:
                            lod_level = int(mmname)
                            print("LOD level:", lod_level)
                        elif numeric_forms_read % 2 == 1:
                            mesh_version = int(mmname)
                            print("Mesh version:", mesh_version)
                        numeric_forms_read += 1

                    # Faces
                    if mmdata["type"] == "chunk" and mmname == "FACE":
                        for f in struct.iter_unpack(
                                face_struct, mmdata["data"]):
                            if f[2] not in used_mtls:
                                used_mtls.append(f[2])
                            if f[6] not in used_altmtls:
                                used_altmtls.append(f[6])

                if out_mode == "json":
                    model_data[cur_model]["lods"].setdefault(
                        lod_level, {"version": mesh_version})
                elif out_mode == "tty":
                    print("--- LOD %d (version %d) ---" %
                          (lod_level, mesh_version))

        if out_mode == "json":
            json.dumps(model_data)

# -*- coding: utf8 -*-
# Blender WCP IFF source exporter script by Kevin Caccamo
# Copyright (C) 2013-2014 Kevin Caccamo
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
from backendcommon import *


def write_iff(filepath,
              start_texnum=22000,
              apply_modifiers=True,
              active_obj_as_lod0=True,
              generate_bsp=False):
    """
    Export a .pas file from the Blender scene.
    The model is exported as a .pas file that can be compiled
    by WCPPascal into a WCP/SO format mesh.
    """

    # Get LOD data and number of LODs
    lod_data = get_lod_data(active_obj_as_lod0)
    if type(lod_data) == tuple:  # tuple means error
        return lod_data
    num_lods = lod_data["num_lods"]

    # Get the hardpoints
    hardpoints = get_hardpoints()

    # Get filename w/o extension
    filename = bpy.path.display_name_from_filepath(filepath)

    # Get texture indices for each material
    mtl_texnums = get_materials(lod_data, start_texnum, apply_modifiers)
    if type(mtl_texnums) == tuple:  # tuple means error
        return mtl_texnums

    outfile = open(filepath, 'w', encoding='utf-8')
    # IFF source file header. If this is not the first line,
    # the file will not compile.
    print('IFF "', filename, '.iff"', '\n',
          sep="", file=outfile)

    print(get_txinfo(mtl_texnums), file=outfile)

    print('{', '\n',
          ' '*2, 'FORM "DETA"', '\n',
          ' '*2, '{', '\n',
          ' '*4, 'CHUNK "RANG"', '\n',
          ' '*4, '{', '\n',
          ' '*6, 'float 0.0', '\n',
          ' '*6, 'float 400.0', '\n',
          ' '*6, 'float 800.0', '\n',
          ' '*4, '}', '\n',
          ' '*4, 'FORM "MESH"', '\n',
          ' '*4, '{', '\n',
          sep='', end='', file=outfile)
    for lod in range(num_lods):
        mesh = lod_data["LOD-" + str(lod)].to_mesh(
            bpy.context.scene, apply_modifiers, "PREVIEW")
        # Required for using tesselated faces (squares and triangles).
        # I decided to use tessfaces for now to keep it simple,
        # but later I may change my mind, since WCSO supports n-gons.
        mesh.calc_tessface()

        mesh.calc_normals()

        # Get unique normals
        unique_normals = set()

        for f in mesh.tessfaces:
            if f.use_smooth:
                for v in f.vertices:
                    # If smoothing is enabled, add the vertex normals
                    nx, ny, nz = mesh.vertices[v].normal
                    unique_normals.add((nx, ny, nz))
            # Add the face normal
            nx, ny, nz = f.normal
            unique_normals.add((nx, ny, nz))

        unique_normals = tuple(unique_normals)

        # Get the references to the normals
        fnrmrefs = list()
        vnrmrefs = list()

        # Face normal indices
        for f in mesh.tessfaces:
            nx, ny, nz = f.normal
            fnrmrefs.append(unique_normals.index((nx, ny, nz)))

        # Vertex normal indices
        for v in mesh.vertices:
            nx, ny, nz = v.normal
            try:
                vnrmrefs.append(unique_normals.index((nx, ny, nz)))
            except ValueError:
                vnrmrefs.append(0)

        # Get the FORM name for this LOD
        lod_num = str(lod).zfill(4)
        print(
            ' '*6, 'FORM "', lod_num, '"', '\n',
            ' '*6, '{', '\n',
            ' '*8, 'FORM "MESH"', '\n',
            ' '*8, '{', '\n',
            ' '*10, 'FORM "0012"', '\n',  # Mesh format version number
            ' '*10, '{', '\n',
            ' '*12, 'CHUNK "NAME"', '\n',
            ' '*12, '{', '\n',
            ' '*14, 'cstring "', filename, '"', '\n',
            sep='', end='', file=outfile)

        # Alias to format method of format string. The format string is being
        # used for nothing more than formatting output values, so I figured
        # I might as well do it this way, plus, it makes code lines shorter.
        ffmt = "float {:.6f}\n".format

        # Vertices
        print(' '*12, '}', '\n',
              ' '*12, 'CHUNK "VERT"', '\n',
              ' '*12, '{',
              sep='', file=outfile)

        write_verts(outfile, mesh.vertices)

        # Normals
        print(' '*12, '}', '\n',
              ' '*12, 'CHUNK "VTNM"', '\n',
              ' '*12, '{',
              sep="", file=outfile)

        write_norms(outfile, unique_normals)

        # Vertices on each face
        print(' '*12, '}', '\n',
              ' '*12, 'CHUNK "FVRT"', '\n',
              ' '*12, '{',
              sep='', file=outfile)

        write_fvrts(outfile, mesh, fnrmrefs, vnrmrefs)

        # Faces
        print(' '*12, '}', '\n',
              ' '*12, 'CHUNK "FACE"', '\n',
              ' '*12, '{',
              sep='', file=outfile)

        write_faces(start_texnum, mtl_texnums, outfile, mesh, fnrmrefs)

        # Location, radius metadata for this LOD
        loc = lod_data["LOD-" + str(lod)].location
        radius = calc_radius(lod_data["LOD-" + str(lod)].dimensions)

        # Center of object
        print('            }', '\n',
              '            CHUNK "CNTR"', '\n',
              '            {', '\n',
              ' '*14, ffmt(loc[0]),  # Center X
              ' '*14, ffmt(loc[1]),  # Center Y
              ' '*14, ffmt(loc[2]),  # Center Z
              '            }', '\n',

              # Radius. Used by object camera
              ' '*12, 'CHUNK "RADI"', '\n',
              ' '*12, '{', '\n',
              ' '*14, ffmt(radius),
              ' '*12, '}', '\n',
              ' '*10, '}', '\n',
              ' '*8, '}', '\n',
              ' '*6, '}', '\n',
              sep='', file=outfile)
    print(' '*4, '}', '\n',
          ' '*4, 'FORM "HARD"', '\n',
          ' '*4, '{',
          sep='', file=outfile)

    # Hardpoints - These will be created from empties prefixed with "hp-"
    for h in hardpoints:
        print(' '*6, 'CHUNK "HARD"', '\n',
              ' '*6, '{', '\n',
              ' '*8, ffmt(h["rot_matrix"][0][0]),
              ' '*8, ffmt(h["rot_matrix"][0][1]),
              ' '*8, ffmt(h["rot_matrix"][0][2]),
              ' '*8, ffmt(h["x"]),     # Hardpoint X
              ' '*8, ffmt(h["rot_matrix"][1][0]),
              ' '*8, ffmt(h["rot_matrix"][1][1]),
              ' '*8, ffmt(h["rot_matrix"][1][2]),
              ' '*8, ffmt(h["z"]),     # Hardpoint Z
              ' '*8, ffmt(h["rot_matrix"][2][0]),
              ' '*8, ffmt(h["rot_matrix"][2][1]),
              ' '*8, ffmt(h["rot_matrix"][2][2]),
              ' '*8, ffmt(h["y"]),     # Hardpoint Y
              ' '*8, 'cstring "', h["name"], '"', '\n',    # Hardpoint name
              ' '*6, '}',
              sep='', file=outfile)

    # Collision, LOD distance metadata
    try:
        # If there is an object named "collsphr" in the scene,
        # use it for the object's collision sphere.
        collsphr = bpy.data.objects["collsphr"]
        if collsphr.type == "EMPTY":
            print("collsphr object found")
            loc = collsphr.location
            radius = max(collsphr.scale) * collsphr.empty_draw_size
        else:
            print("collsphr object must be an empty")
            loc = lod_data["LOD-0"].location
            radius = calc_radius(lod_data["LOD-0"].dimensions)
    except KeyError:
        print("collsphr object not found")
        loc = lod_data["LOD-0"].location
        radius = calc_radius(lod_data["LOD-0"].dimensions)
    print(' '*4, '}', '\n',
          ' '*4, 'FORM "COLL"', '\n',      # Collision info
          ' '*4, '{', '\n',
          ' '*6, 'CHUNK "SPHR"', '\n',   # Collision Sphere
          ' '*6, '{', '\n',
          ' '*8, ffmt(loc[0]),   # Center X
          ' '*8, ffmt(loc[1]),   # Center Y
          ' '*8, ffmt(loc[2]),   # Center Z
          ' '*8, ffmt(radius),   # Radius
          ' '*6, '}', '\n',
          ' '*4, '}', '\n',
          ' '*4, 'CHUNK "FAR "', '\n',
          ' '*4, '{', '\n',
          ' '*6, 'float 0.0', '\n',
          ' '*6, 'float 900000.0', '\n',
          ' '*4, '}', '\n',
          ' '*2, '}', '\n',
          '}', '\n',
          sep='', file=outfile)
    outfile.close()
    return warnings

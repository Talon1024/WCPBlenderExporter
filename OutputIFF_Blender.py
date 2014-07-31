# -*- coding: utf8 -*-
# Blender WCP IFF exporter script by Kevin Caccamo
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

import iff_mesh
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
    # Aliases to long function names
    # Filename without extension
    get_fname = bpy.path.display_name_from_filepath
    # Filename with extension
    get_bname = bpy.path.basename

    # Get directory path of output file, plus filename without extension
    filename = filepath[:filepath.rfind(".")]
    modelname = get_fname(filepath)

    # Create an IFF mesh object
    imesh = iff_mesh.MeshIff(filename)

    # Get LOD data and number of LODs
    lod_data = get_lod_data(active_obj_as_lod0)
    if type(lod_data) == tuple:  # tuple means error
        return lod_data
    num_lods = lod_data["num_lods"]

    # Get the hardpoints
    hardpoints = get_hardpoints()

    # Get texture indices for each material
    mtl_texnums = get_materials(lod_data, start_texnum, apply_modifiers)
    if type(mtl_texnums) == tuple:  # tuple means error
        return mtl_texnums

    mtl_info_file = open(filename + ".txt", 'w', encoding='utf-8')

    print(get_txinfo(mtl_texnums), file=mtl_info_file)

    for lod in range(num_lods):
        bl_mesh = lod_data["LOD-" + str(lod)].to_mesh(
            bpy.context.scene, apply_modifiers, "PREVIEW")
        # Required for using tesselated faces (squares and triangles).
        # I decided to use tessfaces for now to keep it simple,
        # but later I may change my mind, since WCSO supports n-gons.
        bl_mesh.calc_tessface()

        bl_mesh.calc_normals()

        # Get unique normals
        unique_normals = set()

        for f in bl_mesh.tessfaces:
            if f.use_smooth:
                for v in f.vertices:
                    # If smoothing is enabled, add the vertex normals
                    nx, ny, nz = bl_mesh.vertices[v].normal
                    unique_normals.add((nx, ny, nz))
            # Add the face normal
            nx, ny, nz = f.normal
            unique_normals.add((nx, ny, nz))

        unique_normals = tuple(unique_normals)

        # Get the references to the normals
        fnrmrefs = list()
        vnrmrefs = list()

        # Face normal indices
        for f in bl_mesh.tessfaces:
            nx, ny, nz = f.normal
            fnrmrefs.append(unique_normals.index((nx, ny, nz)))

        # Vertex normal indices
        for v in bl_mesh.vertices:
            nx, ny, nz = v.normal
            try:
                vnrmrefs.append(unique_normals.index((nx, ny, nz)))
            except ValueError:
                vnrmrefs.append(0)

        # Create an IFF mesh LOD object for this LOD
        imeshl = iff_mesh.MeshLODForm(lod)

        # Name
        imeshl_name = imeshl.get_name_chunk()
        imeshl_name.add_member(modelname)

        # Vertices
        imeshl_verts = imeshl.get_vert_chunk()
        for v in bl_mesh.vertices:
            vx, vy, vz = v.co[:]
            imeshl_verts.add_member(float(vx))
            imeshl_verts.add_member(float(-vy))
            imeshl_verts.add_member(float(vz))

        # Normals
        imeshl_norms = imeshl.get_vtnm_chunk()
        for n in unique_normals:
            nx, ny, nz = n[:]
            imeshl_norms.add_member(float(nx))
            imeshl_norms.add_member(float(-ny))
            imeshl_norms.add_member(float(nz))

        # Vertices on each face
        imeshl_fvrts = imeshl.get_fvrt_chunk()

        fnrm_idx = 0
        uv_map = bl_mesh.tessface_uv_textures.active.data
        for f, u in zip(bl_mesh.tessfaces, uv_map):
            for v, uv in zip(f.vertices, u.uv):
                if f.use_smooth:
                    # If smoothing is enabled, use the vertex normal
                    vtnm_idx = vnrmrefs[v]
                else:
                    # Otherwise, use the face normal
                    vtnm_idx = fnrmrefs[fnrm_idx]
                vert_idx = v
                uvX, uvY = uv
                imeshl_fvrts.add_member(vert_idx)
                imeshl_fvrts.add_member(vtnm_idx)
                imeshl_fvrts.add_member(uvX)
                # -uvY allows textures to be converted without the
                # modder having to vertically flip them.
                imeshl_fvrts.add_member(-uvY)
            fnrm_idx += 1

        # Faces
        imeshl_faces = imeshl.get_face_chunk()

        fvrt_idx = 0
        cur_face_idx = 0
        for f in range(len(bl_mesh.tessfaces)):
            cur_face = bl_mesh.tessfaces[f]  # Alias to current face

            # If the face has a material with an image texture,
            # get the corresponding texture number
            facemtl = bl_mesh.materials[cur_face.material_index]
            facetex = facemtl.active_texture
            if facetex.type == "IMAGE":
                matfilename = get_bname(facetex.image.filepath)
                texnum = mtl_texnums[matfilename]
            else:
                # Otherwise, use the default texture number
                texnum = start_texnum

            # If the material on the face is shadeless,
            # set the corresponding lighting bitflag.
            # More bitflags will be added as they are discovered.
            light_flags = 0
            if facemtl.use_shadeless:
                light_flags |= LFLAG_FULLBRIGHT
            if "light_flags" in facemtl:
                # If the user has defined a custom value to
                # use for the lighting bitflag, override the
                # calculated value with the custom value.
                try:
                    light_flags = int(facemtl["light_flags"])
                except ValueError:
                    light_flags = 0
                    print("Cannot convert", facemtl["light_flags"], "to an "
                          "integer value!")

            num_verts = len(cur_face.vertices)

            vtnm_idx = fnrmrefs[cur_face_idx]

            # Vertex coordinates and normals are needed
            # in order to calculate the D-Plane.
            first_vert = bl_mesh.vertices[cur_face.vertices[0]].co
            face_nrm = cur_face.normal
            dplane = calc_dplane(first_vert, face_nrm)

            imeshl_faces.add_member(vtnm_idx)     # Face normal
            imeshl_faces.add_member(dplane)       # D-Plane
            imeshl_faces.add_member(texnum)       # Texture number
            imeshl_faces.add_member(fvrt_idx)     # Index of face's first FVRT
            imeshl_faces.add_member(num_verts)    # Number of vertices
            imeshl_faces.add_member(light_flags)  # Lighting flags
            imeshl_faces.add_member(0x7F0096FF)   # Unknown

            fvrt_idx += num_verts
            cur_face_idx += 1

        # Location, radius metadata for this LOD
        loc = lod_data["LOD-" + str(lod)].location
        radius = calc_radius(lod_data["LOD-" + str(lod)].dimensions)

        # Center of object
        imeshl_cntr = imeshl.get_cntr_chunk()
        imeshl_cntr.add_member(loc[0])  # Center X
        imeshl_cntr.add_member(loc[1])  # Center Y
        imeshl_cntr.add_member(loc[2])  # Center Z

        # Radius
        imeshl_radi = imeshl.get_radi_chunk()
        imeshl_radi.add_member(radius)
        imesh.get_meshes_form().add_member(imeshl)

    # Hardpoints - These will be created from empties prefixed with "hp-"
    for h in hardpoints:
        imesh.add_hardpt(**h)

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
    imesh.make_coll_sphr(loc[0], loc[1], loc[2], radius)
    imesh.write_file_bin()
    return warnings

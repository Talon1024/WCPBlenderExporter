#  Blender WCP IFF source exporter script by Kevin Caccamo
#  Copyright (C) 2013 Kevin Caccamo
#  E-mail: kevin@ciinet.org
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, see <http://www.gnu.org/licenses/>.
#
# <pep8-80 compliant>

import iff_mesh
import bpy
from math import sin, cos
from collections import OrderedDict

MAX_NUM_LODS = 3
LOD_NAMES = ["detail-" + str(lod) for lod in range(MAX_NUM_LODS)]
LFLAG_FULLBRIGHT = 2


def calc_rot_matrix(rx, ry, rz):
    """
    Calculate a rotation matrix from a set of rotations
    on the x, y, and z axes.

    Calculates a rotation matrix for each axis,
    and then multiplies the results together.
    Blender's rotation matrix multiplication doesn't work correctly...
    Rotations are in eulers (radians).
    """

    cx = cos(rx)
    sx = sin(rx)
    cy = cos(ry)
    sy = sin(ry)
    cz = cos(rz)
    sz = sin(rz)

    # Thanks to Wikipedia (Rotation matrix) and
    # http://www.idomaths.com/linear_transformation_3d.php
    matrix_x = [[1,  0,   0],
                [0,  cx, sx],
                [0, -sx, cx]]
    matrix_y = [[cy, 0, -sy],
                [0,  1,   0],
                [sy, 0,  cy]]
    matrix_z = [[cz,  sz, 0],
                [-sz, cz, 0],
                [0,   0,  1]]

    # From http://nghiaho.com/?page_id=846: R = ZYX
    rot_matrix = multiply_3x3_matrices(matrix_z, matrix_y)
    rot_matrix = multiply_3x3_matrices(rot_matrix, matrix_x)
    return rot_matrix


def multiply_3x3_matrices(matrix1, matrix2):
    """
    Multiplies two 3x3 matrices together and
    returns the resulting matrix.
    """
    result_matrix = [

        # First row
        # First row of matrix1 * first column of matrix2
        [matrix1[0][0] * matrix2[0][0] +
         matrix1[0][1] * matrix2[1][0] +
         matrix1[0][2] * matrix2[2][0],

        # First row of matrix1 * second column of matrix2
         matrix1[0][0] * matrix2[0][1] +
         matrix1[0][1] * matrix2[1][1] +
         matrix1[0][2] * matrix2[2][1],

        # First row of matrix1 * third column of matrix2
         matrix1[0][0] * matrix2[0][2] +
         matrix1[0][1] * matrix2[1][2] +
         matrix1[0][2] * matrix2[2][2]],

        # Second row
        # Second row of matrix1 * first column of matrix2
        [matrix1[1][0] * matrix2[0][0] +
         matrix1[1][1] * matrix2[1][0] +
         matrix1[1][2] * matrix2[2][0],

        # Second row of matrix1 * second column of matrix2
         matrix1[1][0] * matrix2[0][1] +
         matrix1[1][1] * matrix2[1][1] +
         matrix1[1][2] * matrix2[2][1],

        # Second row of matrix1 * third column of matrix2
         matrix1[1][0] * matrix2[0][2] +
         matrix1[1][1] * matrix2[1][2] +
         matrix1[1][2] * matrix2[2][2]],

        # Third row
        # Third row of matrix1 * first column of matrix2
        [matrix1[2][0] * matrix2[0][0] +
         matrix1[2][1] * matrix2[1][0] +
         matrix1[2][2] * matrix2[2][0],

        # Third row of matrix1 * second column of matrix2
         matrix1[2][0] * matrix2[0][1] +
         matrix1[2][1] * matrix2[1][1] +
         matrix1[2][2] * matrix2[2][1],

        # Third row of matrix1 * third column of matrix2
         matrix1[2][0] * matrix2[0][2] +
         matrix1[2][1] * matrix2[1][2] +
         matrix1[2][2] * matrix2[2][2]]
    ]
    return result_matrix


def get_lod_data(ACTIVE_OBJ_AS_LOD0):
    """Get the level of detail data pertinent to the game engine"""
    num_lods = 0

    # Get the LOD data
    lod_data = dict()
    ob = bpy.context.active_object
    for lod in range(MAX_NUM_LODS):
        if lod == 0:    # LOD 0 can either be the active object or detail-0
            # If the user wants to use the active object...
            if (ACTIVE_OBJ_AS_LOD0 and
                    ob.type == "MESH" and
                    ob.name not in LOD_NAMES):
                lod_data["LOD-" + str(lod)] = ob
                num_lods += 1
            else:    # Otherwise, use the detail-0 object
                try:
                    lod_data["LOD-" + str(lod)] = (
                        bpy.data.objects[LOD_NAMES[lod]])
                    if bpy.data.objects[LOD_NAMES[lod]].type != "MESH":
                        error_msg = LOD_NAMES[lod] + " is not a mesh!"
                        return ({"ERROR"}, error_msg)
                    num_lods += 1
                except KeyError:
                    error_msg = ("Cannot find an object named " +
                                 LOD_NAMES[lod] + "!")
                    print(error_msg)
                    return ({"ERROR"}, error_msg)
        else:   # Other LODs
            try:
                lod_data["LOD-" + str(lod)] = (
                    bpy.data.objects[LOD_NAMES[lod]])
                num_lods += 1
            except KeyError:
                print("Unable to find a mesh for LOD " + str(lod))
    lod_data["num_lods"] = num_lods
    return lod_data


def get_hardpoints():
    """
    For all empties named "hp-xxxx" in the scene,
    converts them to hardpoint dictionaries.
    Returns a list of hardpoint dictionaries.
    """
    hardpoints = []
    for o in bpy.data.objects:
        if o.type == "EMPTY" and o.name.startswith("hp-") and not o.hide:
            rot_matrix = calc_rot_matrix(o.rotation_euler.x,
                                         o.rotation_euler.z,
                                         o.rotation_euler.y)
            hardpoints.append({"x": o.location.x,
                               "y": o.location.z,
                               "z": o.location.y,
                               "rot_matrix": rot_matrix,
                               "name": o.name[3:]})
    return hardpoints


def calc_radius(dim):
    """Calculate the radius of the model.

    Radius is calculated by dividing the highest dimension (diameter) by 2.
    """
    max_bb = max(dim)
    radius = max_bb / 2
    return radius


def calc_dplane(vert, facenrm):
    """Calculate the D-Plane of the face.

    vert refers to the first vertex of the face
    facenrm refers to the face normal
    The D-Plane is used by the VISION engine for backface culling
    Thanks to gr1mre4per from CIC for the algorithm!
    """
    dplane = -((facenrm[0] * vert[0]) +
               (facenrm[1] * vert[1]) +
               (facenrm[2] * vert[2]))
    return dplane


def get_first_texture_slot(mtl):
    for mtex in reversed(mtl.texture_slots):
        if mtex:
            return mtex
    else:
        return None


def get_materials(lod_data, start_texnum, apply_modifiers):
    """Convert all of the named material textures to texture indices.
    Returns a mapping from material texture filenames to texture indices."""
    # Aliases to long function names
    get_fname = bpy.path.display_name_from_filepath  # Filename w/o extension
    get_bname = bpy.path.basename  # Filename with extension

    num_lods = lod_data["num_lods"]
    # Use OrderedDict to retain order of texture -> texnum
    mtl_texnums = OrderedDict()  # Texture filename -> texture number mapping
    used_mtls = []  # Materials used by the mesh

    # Get all of the material names used in each LOD mesh.
    for lod in range(num_lods):
        mesh = lod_data["LOD-" + str(lod)].to_mesh(
            bpy.context.scene, apply_modifiers, "PREVIEW")
        for f in mesh.tessfaces:
            cur_mtl = mesh.materials[f.material_index].name
            if cur_mtl not in used_mtls:
                used_mtls.append(cur_mtl)

    # Get the textures and associate each texture with a material number,
    # beginning at the user's specified starting texture number.
    num_textures = 0
    for mtl_name in used_mtls:
        curr_mtl = bpy.data.materials[mtl_name]
        curr_tx = get_first_texture_slot(curr_mtl)
        curr_txnum = start_texnum + num_textures

        if curr_tx.type == "IMAGE":
            img_bname = get_bname(curr_tx.image.filepath)
            img_fname = get_fname(curr_tx.image.filepath)
            if img_fname.isnumeric():
                # If the filename is numeric, use it as the texture index.
                img_num = int(img_fname)
                if img_num >= 0 and img_num <= 99999990:
                    # What if the user has two numeric image filenames that
                    # are the same number? i.e. 424242.jpg and 424242.png
                    if img_num not in mtl_texnums.values():
                        mtl_texnums[img_bname] = img_num
                    else:
                        mtl_texnums[img_bname] = curr_txnum
                        print(img_fname, "is already in use! Using",
                            curr_txnum, "instead.")
                        num_textures += 1
                else:
                    # If the number is too big, use the "default" value.
                    mtl_texnums[img_bname] = curr_txnum
                    print(img_fname, "is too big a number",
                          "to be used as a texture number! Using",
                          curr_txnum, "instead.")
                    num_textures += 1
            # If the image filename is not numeric,
            # refer to the user's starting texture number.
            else:
                if img_bname not in mtl_texnums.keys():
                    mtl_texnums[img_bname] = curr_txnum
                    num_textures += 1
        else:
            error_msg = curr_tx.name + " is not an image texture."
            print(error_msg)
            return ({"ERROR"}, error_msg)
    return mtl_texnums


def get_txinfo(mtl_texnums, as_comment=False):
    """Gets a string showing the Image Filename->Texture number"""
    # Used to make the Image Filename->Material Number list
    # easier to read.
    # max_width = len(max(mtl_texnums.keys(), key=len))
    # Print Image Filename->Material Number information for the
    # user to use as a guide for converting textures.
    tx_info = ""
    for img_fname, texnum in sorted(
            mtl_texnums.items(),
            key=lambda mattex: mattex[1]):
        if as_comment:
            tx_info += "// "
        tx_info += "{} --> {!s:0>8}.mat\n".format(img_fname, texnum)
    return tx_info


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

        #Name
        imeshl_name = imeshl.get_name_chunk()
        imeshl_name.add_member(modelname)

        #Vertices
        imeshl_verts = imeshl.get_vert_chunk()
        for v in bl_mesh.vertices:
            vx, vy, vz = v.co[:]
            imeshl_verts.add_member(float(vx))
            imeshl_verts.add_member(float(-vy))
            imeshl_verts.add_member(float(vz))

        #Normals
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

        #Faces
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

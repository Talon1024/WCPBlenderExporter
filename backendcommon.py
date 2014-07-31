# Common methods used by both the IFF and PAS exporters

from math import sin, cos
from collections import OrderedDict

MAX_NUM_LODS = 3
LOD_NAMES = ["detail-" + str(lod) for lod in range(MAX_NUM_LODS)]
LFLAG_FULLBRIGHT = 2
# Non-critical warnings will be reported to Blender. Critical errors will be
# exceptions.
warnings = []


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
    for lod in range(MAX_NUM_LODS):
        ob = None
        lod_ob_name = LOD_NAMES[lod]
        if lod == 0:    # LOD 0 can either be the active object or detail-0
            # If the user wants to use the active object...
            ob = bpy.context.active_object
            if (ACTIVE_OBJ_AS_LOD0 and
                    ob.name != lod_ob_name):
                if ob.type == "MESH":
                    ob = bpy.context.active_object
                    lod_data["LOD-" + str(lod)] = ob
                    num_lods += 1
                else:
                    error_msg = "Object " + ob.name + " is not a mesh!"
                    warnings.append(({"INFO"}, error_msg))
                    ob = bpy.data.objects[lod_ob_name]
                    try:
                        lod_data["LOD-" + str(lod)] = ob
                        if ob.type != "MESH":
                            error_msg = lod_ob_name + " is not a mesh!"
                            raise TypeError(error_msg)
                        num_lods += 1
                    except KeyError:
                        error_msg = ("Cannot find an object named " +
                                     lod_ob_name + "!")
                        raise KeyError(error_msg)
            else:    # Otherwise, use the detail-0 object
                ob = bpy.data.objects[lod_ob_name]
                try:
                    lod_data["LOD-" + str(lod)] = ob
                    if ob.type != "MESH":
                        error_msg = lod_ob_name + " is not a mesh!"
                        raise TypeError(error_msg)
                    num_lods += 1
                except KeyError:
                    error_msg = ("Cannot find an object named " +
                                 lod_ob_name + "!")
                    raise KeyError(error_msg)
        else:   # Other LODs
            try:
                ob = bpy.data.objects[lod_ob_name]
                lod_data["LOD-" + str(lod)] = ob
                num_lods += 1
            except KeyError:
                error_msg = "Unable to find a mesh for LOD " + str(lod)
                warnings.append(({"INFO"}, error_msg))
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
        curr_tx = get_first_texture_slot(curr_mtl).texture
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
            raise TypeError(error_msg)
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
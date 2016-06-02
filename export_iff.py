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

import bpy
import mathutils
import warnings
import re
import array
from os import sep as dirsep
from . import iff_mesh
from math import sin, cos
from collections import OrderedDict, namedtuple
from itertools import repeat

LFLAG_UNKNOWN1 = 1
LFLAG_FULLBRIGHT = 2
LFLAG_UNKNOWN2 = 8

# Name pattern for LOD objects. Largely deprecated in favour of named LOD
# object models. Mostly present for backwards compatibility.
# Group 1 is the LOD level number.
MAIN_LOD_RE = re.compile(r"^detail-(\d+)$")

# Name pattern for LOD objects, grouped by name.
# Group 1 is the child object name, group 2 is the LOD level number.
CHLD_LOD_RE = re.compile(r"^(\w+)-lod(\d+)$")

# Name pattern for hardpoints. Group 1 is the hardpoint name, group 2 is
# the suffix appended by Blender to objects with conflicting names.
HARDPOINT_RE = re.compile(r"^hp-(\w+)(?:\.\d*)?$")

# Non-critical warnings will be reported to Blender. Critical errors will be
# exceptions.


class KeyWarning(Warning):
    pass


class TypeWarning(Warning):
    pass


class ValueWarning(Warning):
    pass


class ModelManager:
    # Manages the LODs for a mesh to export.
    # Each instance of this class should be exportable to a mesh IFF.
    # Scans for a base LOD mesh and other related LODs in a given scene.

    # One of the asteroid models I've looked at (AST_G_01.IFF) has 7 LODs
    MAX_NUM_LODS = 7

    # The LOD base object is a LOD for the main model.
    LOD_NSCHEME_DETAIL = 0

    # The LOD base object is a LOD for a child model, or the main model if user
    # decides to set the active object as LOD 0.
    LOD_NSCHEME_CHLD = 1

    # Name pattern for LOD range info. Group 1 is the range, group 2 is the
    # suffix appended by Blender to objects with conflicting names.
    DRANGE_RE = re.compile(r"^drang=([0-9,]+)(?:\.\d*)?$")

    # prefix for CNTR/RADI spheres
    CNTRADI_PFX = "cntradi"

    # prefix for spherical collider definition objects
    COLLSPHR_PFX = "collsphr"

    # prefix for BSP collider definition objects
    COLLMESH_PFX = "collmesh"

    def __init__(self, base_name, base_obj, use_facetex, drang_increment,
                 gen_bsp, scene_name):

        if not isinstance(base_name, str):
            raise TypeError("Export filename must be a string!")
        if scene_name not in bpy.data.scenes:
            raise TypeError("scene must be the name of a Blender scene!")
        if base_obj not in bpy.data.scenes[scene_name].objects:
            raise TypeError("base_obj must be the name of a Blender mesh "
                            "object in the given scene!")

        self.scene = scene_name  # Name of the scene to use
        self.base_name = base_name  # Model base name (ex. Duhiky)
        self._exp_fname = base_name  # Export filename
        self.name_scheme = 0  # See LOD_NSCHEME constants above
        self.base_obj = base_obj  # Name of base object (ex. Duhiky-lod0)
        self.base_parent = str(
            bpy.data.scenes[scene_name].objects[base_obj].parent)
        base_lod = self._get_lod(base_obj, True)  # Determine base object LOD

        # Names of LOD objects
        self.lods = [None for x in range(self.MAX_NUM_LODS)]

        self.lodms = []  # LOD object meshes (converted from objects)
        self.lods[base_lod] = base_obj
        self.hardpoints = []  # Hardpoints
        self.hpobnames = []  # Hardpoint Blender object names
        self.dranges = [float(0)]  # LOD ranges (RANG chunk)
        self.drang_increment = drang_increment
        self.dsphrs = []  # CNTR/RADI spheres for each LOD.
        self.gen_bsp = gen_bsp
        self.collider = None  # COLL form
        self.use_mtltex = not use_facetex
        self.textures = []  # Textures for all LODs
        self.mtltexs = {}  # Material -> texture dict
        self.children = []  # Child objects
        self.setup_complete = False

    def _get_parent(self, chld_obj):
        parent = None
        pparent = None
        if chld_obj.parent is not None:
            parent = chld_obj.parent
            pparent = _get_parent(chld_obj.parent)
        return pparent, parent

    def _get_lod(self, lod_obj, base=False):
        lod = MAIN_LOD_RE.match(lod_obj)
        if lod:
            if base:
                self.name_scheme = self.LOD_NSCHEME_DETAIL
                warnings.warn("detail-x LOD naming scheme is deprecated.",
                              DeprecationWarning)
            lod = int(lod.group(1))
            return lod

        lod = CHLD_LOD_RE.match(lod_obj)
        if lod:
            if base:
                self.name_scheme = self.LOD_NSCHEME_CHLD
            self.base_name = lod.group(1)
            lod = int(lod.group(2))
            return lod

        # Assume LOD 0, and "child" LOD naming scheme
        if base:
            self.name_scheme = self.LOD_NSCHEME_CHLD
        return 0

    def texs_for_mtl(self, material):
        if not isinstance(material, bpy.types.Material):
            raise TypeError("You must provide a Blender material in order to "
                            "get its valid textures!")

        filled_slots = 0
        valid_slots = []
        for ts in material.texture_slots:
            if ts is not None:
                filled_slots += 1
            if (ts is not None and
                    isinstance(ts, bpy.types.MaterialTextureSlot) and
                    ts.texture_coords == "UV" and
                    isinstance(ts.texture, bpy.types.ImageTexture) and
                    ts.texture.image is not None):
                valid_slots.append(ts.texture)

        if filled_slots > 0 and len(valid_slots) == 0:
            raise ValueError(
                "Found no valid texture slots out of the ones that were "
                "filled! In order for a texture slot to be valid, it must be "
                "a UV-mapped image texture.")

        return valid_slots

    def setup(self):
        # Scan for valid LOD objects related to the base LOD object
        for lod in range(self.MAX_NUM_LODS):
            lod_name = ""
            if self.name_scheme == self.LOD_NSCHEME_DETAIL:
                lod_name = "detail-{}".format(lod)
            elif self.name_scheme == self.LOD_NSCHEME_CHLD:
                lod_name = "{}-lod{}".format(self.base_name, lod)

            if (lod_name in bpy.data.scenes[self.scene].objects and
                    lod_name != self.base_obj):
                if self.lods[lod] is None:
                    if (bpy.data.scenes[self.scene]
                            .objects[lod_name].type == 'MESH'):
                        if (bpy.data.scenes[self.scene]
                                    .objects[lod_name].hide is False):
                                if (str(bpy.data.scenes[self.scene]
                                        .objects[lod_name].parent) !=
                                        self.base_parent):
                                    warnings.warn(
                                        "The LOD objects for this model have "
                                        "different parents!", ValueWarning)
                                self.lods[lod] = lod_name
                    else:
                        raise TypeError("Object {} is not a mesh!".format(
                                        lod_name))
                else:
                    raise ValueError(
                        "Tried to set LOD {} to object {}, but it was already "
                        "set to object {}!".format(lod, lod_name,
                                                   self.lods[lod]))

        # Ensure the LODs array is consistent
        if self.lods[0] is None:
            raise TypeError("The first LOD (LOD 0) of the model must exist!")

        no_lod_idx = None  # Index for first blank LOD

        for lod_idx, lod_obj in enumerate(self.lods):
            if no_lod_idx is None:
                if lod_obj is None:
                    no_lod_idx = lod_idx
            else:
                if lod_obj is not None:
                    raise TypeError(
                        "Inconsistent LODs. A LOD object was found after lod "
                        "{} ({}).".format(no_lod_idx, lod_obj))

        if no_lod_idx is not None:
            self.lods = self.lods[:no_lod_idx]

        del no_lod_idx

        print("LOD object names:", self.lods)

        # Initialize lists that should be the same length as self.lods

        # Get LOD ranges for this model
        for lod_idx in range(len(self.lods)):
            if lod_idx > 0:
                # LOD Ranges are only valid for LODs greater than 0
                for obj in bpy.data.scenes[self.scene].objects:
                    if (obj.parent is not None and
                        obj.parent.name == self.lods[lod_idx] and
                        obj.type == "EMPTY" and obj.hide is False and
                            self.DRANGE_RE.match(obj.name)):
                        drange = self.DRANGE_RE.match(obj.name).group(1)
                        drange = drange.translate({44: 46})  # Comma to period
                        drange = float(drange)
                        self.dranges.append(drange)
                        break
                else:
                    self.dranges.append(None)

        print("dranges (b4):", self.dranges)

        # Fill in blank LOD ranges
        for dr_idxa in range(len(self.dranges)):
            if self.dranges[dr_idxa] is None:
                drange_before = self.dranges[dr_idxa - 1]
                empty_dranges = 0

                # Find closest value for drange_after
                for dr_idxb in range(dr_idxa, len(self.dranges)):
                    if self.dranges[dr_idxb] is not None:
                        break
                    else:
                        empty_dranges += 1

                try:
                    drange_after = self.dranges[dr_idxa + empty_dranges]
                except IndexError:
                    # There's no known detail ranges after this one,
                    # so generate them
                    drange_after = (self.drang_increment *
                                    (empty_dranges + 1) + drange_before)

                if drange_after < drange_before:
                    raise ValueError("Each detail range must be greater than "
                                     "the one before it!")

                # Find interval and index of last detail range
                drange_interval = (
                    (drange_after - drange_before) /
                    (empty_dranges + 1))

                dridx_end = dr_idxa + empty_dranges

                # Fill in the missing values
                # Best list comprehension ever LOL.
                self.dranges[dr_idxa:dridx_end] = [
                    x * n + drange_before for x, n in zip(
                        repeat(drange_interval, empty_dranges),
                        range(1, empty_dranges + 1)
                    )]

        print("dranges (after):", self.dranges)

        # Get CNTR/RADI data for each LOD
        for lod_idx in range(len(self.lods)):
            for obj in bpy.data.scenes[self.scene].objects:
                if (obj.parent is not None and
                    obj.parent.name == self.lods[lod_idx] and
                    obj.name.lower().startswith(self.CNTRADI_PFX) and
                    obj.type == "EMPTY" and obj.hide is False and
                        obj.empty_draw_type == "SPHERE"):
                    # Convert Blender to VISION coordinates.
                    x, z, y = obj.location
                    self.dsphrs.append(iff_mesh.Sphere(
                        x, y, z, max(obj.scale)
                    ))
                    break
            else:
                # Generate CNTR/RADI sphere
                lod_obj = (
                    bpy.data.scenes[self.scene].objects[self.lods[lod_idx]])

                x, z, y = lod_obj.location
                r = max(lod_obj.dimensions) / 2
                self.dsphrs.append(iff_mesh.Sphere(x, y, z, r))

            print("""LOD {}
X: {}
Y: {}
Z: {}
radius: {}""".format(lod_idx, x, y, z, r))

        # Get the hardpoints associated with this model
        for lod_idx in range(len(self.lods)):
            for obj in bpy.data.scenes[self.scene].objects:
                if (obj.parent is not None and
                    obj.parent.name == self.lods[lod_idx] and
                    obj.type == "EMPTY" and obj.hide is False and
                        HARDPOINT_RE.match(obj.name)):
                    hpname = HARDPOINT_RE.match(obj.name).group(1)
                    hpmatrix = obj.rotation_euler.to_matrix().to_3x3()
                    hardpt = iff_mesh.Hardpoint(hpmatrix, obj.location, hpname)
                    self.hardpoints.append(hardpt)
                    self.hpobnames.append(obj.name)

        # Ensure there are no hardpoint name conflicts
        hpnames = []
        for hp in self.hardpoints:
            if hp.name in hpnames:
                raise ValueError("Two or more hardpoints of the object {} "
                                 "have the same name ({})! (Hardpoint name is "
                                 "stripped of numeric extension)".format(
                                     self.base_name, hp.name
                                 ))
            hpnames.append(hp.name)
        del hpnames

        print("========== Hardpoints ==========")
        for hp, hpob in zip(self.hardpoints, self.hpobnames):
            print(hp, ": ({})".format(hpob))

        # Get the collider for this model
        if not self.gen_bsp:
            for lod_idx in reversed(range(len(self.lods))):
                for obj in bpy.data.scenes[self.scene].objects:
                    if (obj.parent is not None and
                        obj.parent.name == self.lods[lod_idx] and
                        obj.name.lower().startswith(self.COLLSPHR_PFX) and
                        obj.type == "EMPTY" and obj.hide is False and
                            obj.empty_draw_type == "SPHERE"):
                        x, z, y = obj.location
                        radius = max(obj.scale)
                        self.collider = iff_mesh.Collider(
                            "sphere", iff_mesh.Sphere(x, y, z, radius)
                        )
                        break

            if self.collider is None:
                # Generate collsphr
                lod_obj = bpy.data.scenes[self.scene].objects[self.lods[0]]
                x, z, y = lod_obj.location
                radius = max(lod_obj.dimensions) / 2
                self.collider = iff_mesh.Collider(
                    "sphere", iff_mesh.Sphere(x, y, z, radius)
                )
        else:
            raise NotImplementedError(
                "BSP Tree generation is not yet supported!")

        print("Collider:", self.collider)

        # Convert all LOD objects to meshes to populate the LOD mesh list.
        for lod in self.lods:
            self.lodms.append(bpy.data.scenes[self.scene].objects[lod].to_mesh(
                bpy.data.scenes[self.scene], True, "PREVIEW"))

        # Get the textures used by all LODs for this model
        used_materials = []
        for lodmi in range(len(self.lodms)):
            self.lodms[lodmi].calc_tessface()
            # tf_mtl = None  # The material for this tessface
            # tf_mlf = 0  # The light flags for this tessface
            # tf_mtf = False  # Is the material a flat colour
            if self.use_mtltex:
                # Material textures
                for tf in self.lodms[lodmi].tessfaces:
                    # Ensure material for this face exists
                    try:
                        tf_mtl = self.lodms[lodmi].materials[tf.material_index]
                    except IndexError:
                        raise ValueError("You must have a valid material "
                                         "assigned to each face!")

                    if tf_mtl not in used_materials:
                        used_materials.append(tf_mtl)
            else:
                # Face textures (visible in Multitexture viewport render mode)
                for tf, tfuv in zip(
                        self.lodms[lodmi].tessfaces,
                        self.lodms[lodmi].tessface_uv_textures.active.data):
                    if (tfuv.image is not None and
                            tfuv.image not in used_materials):
                        # Use the face image
                        used_materials.append(tfuv.image)
                    else:
                        # Use the face material colour
                        tf_mtl = self.lodms[lodmi].materials[tf.material_index]
                        tf_clr = iff_mesh.colour_texnum(tf_mtl.diffuse_color)

                        if tf_clr not in used_materials:
                            used_materials.append(tf_clr)

        # Get information about materials.
        # TODO: Find out how best to associate the new materials with the
        # individual faces.
        # REVIEW: Ensure all "mtldata" tuples use the same format.
        if self.use_mtltex:
            for tf_mtl in used_materials:

                # Get light flags for this material
                if tf_mtl.get("light_flags") is not None:
                    tf_mlf = int(tf_mtl.get("light_flags"))
                elif tf_mtl.use_shadeless:
                    tf_mlf = LFLAG_FULLBRIGHT
                else:
                    tf_mlf = 0

                tf_mtexs = self.texs_for_mtl(tf_mtl)  # Valid texture slots

                if len(tf_mtexs) == 0:
                    # Flat colour material; Use the colour of the material.
                    tf_mtf = True
                    tf_img = iff_mesh.colour_texnum(tf_mtl.diffuse_color)
                else:
                    # Textured material; Use first valid texture slot.
                    tf_mtf = False
                    tf_img = tf_mtexs[0].image

                mtldata = (tf_mtf, tf_mlf, tf_img)
                if mtldata not in self.textures:
                    self.mtltexs[tf_mtl] = len(self.textures)
                    self.textures.append(mtldata)
        else:
            for tf_mtl in used_materials:
                tf_mlf = 0
                tf_mtf = True if isinstance(tf_mtl, int) else False

                mtldata = (tf_mtf, tf_mlf, tf_img)
                if mtldata not in self.textures:
                    self.mtltexs[tf_mtl] = len(self.textures)
                    self.textures.append(mtldata)

        print("Materials used by this model:")
        for mtl in self.textures:
            print(mtl[2], "Light flags:", mtl[1],
                  "(Flat)" if mtl[0] else "(Textured)")

        self.setup_complete = True

    @property
    def exp_fname(self):
        """The export filename.

        The model is written to disk with this filename, suffixed by '.iff'
        For example, if the export filename is 'Duhiky', the file for this
        model will be 'Duhiky.iff'"""
        return self._exp_fname

    @exp_fname.setter
    def exp_fname(self, value):
        if not isinstance(value, str):
            raise TypeError("Export filename must be a string!")

        self._exp_fname = value

    @exp_fname.deleter
    def exp_fname(self):
        self._exp_fname = self.base_name


class ExportBackend:

    def __init__(self,
                 filepath,
                 start_texnum=22000,
                 apply_modifiers=True,
                 export_active_only=True,
                 use_facetex=False,
                 wc_orientation_matrix=None,
                 include_far_chunk=True,
                 drang_increment=500.0,
                 generate_bsp=False):
        self.filepath = filepath
        self.start_texnum = start_texnum
        self.apply_modifiers = apply_modifiers
        self.export_active_only = export_active_only
        self.use_facetex = use_facetex
        self.wc_orientation_matrix = wc_orientation_matrix
        self.include_far_chunk = include_far_chunk
        self.drang_increment = drang_increment
        self.generate_bsp = generate_bsp

    def calc_dplane(self, vert, facenrm):
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

    def get_materials(self):
        """Convert all of the named material textures to
        texture indices.

        Returns a mapping from material texture filenames
        to texture indices."""
        # Aliases to long function names
        # Filename w/o extension
        get_fname = bpy.path.display_name_from_filepath
        # Filename with extension
        get_bname = bpy.path.basename

        num_lods = lod_data["num_lods"]
        # Use OrderedDict to retain order of texture -> texnum
        # Texture filename -> texture number mapping
        mtl_texnums = OrderedDict()
        # Materials used by the mesh
        used_mtls = []

        # Get all of the material names used in each LOD mesh.
        for lod in range(num_lods):
            mesh = lod_data["LOD-" + str(lod)].to_mesh(
                bpy.context.scene, self.apply_modifiers, "PREVIEW")
            if self.use_facetex:
                active_idx = None
                for idx, texmap in enumerate(mesh.tessface_uv_textures):
                    if texmap.active:
                        active_idx = idx
                        break
                for f in mesh.tessface_uv_textures[active_idx].data:
                    used_mtls.append(get_bname(f.image.filepath))
            else:
                for f in mesh.tessfaces:
                    cur_mtl = mesh.materials[f.material_index].name
                    if cur_mtl not in used_mtls:
                        used_mtls.append(cur_mtl)

        # Get the textures and associate each texture with a material number,
        # beginning at the user's specified starting texture number.
        num_textures = 0
        for mtl_name in used_mtls:
            curr_txnum = self.start_texnum + num_textures
            if self.use_facetex:
                img_bname = get_bname(mtl_name)
                img_fname = get_fname(mtl_name)
                print(img_fname)
                if img_fname.isnumeric():
                    # If the filename is numeric, use it as the
                    # texture index.
                    img_num = int(img_fname)
                    if img_num >= 0 and img_num <= 99999990:
                        if img_num != curr_txnum:
                            mtl_texnums[img_bname] = img_num
                        else:
                            mtl_texnums[img_bname] = curr_txnum
                            print(img_fname, "is already in use! Using",
                                  curr_txnum, "instead.")
                            num_textures += 1
                else:
                    if img_bname not in mtl_texnums.keys():
                        mtl_texnums[img_bname] = curr_txnum
                        num_textures += 1
            else:
                curr_mtl = bpy.data.materials[mtl_name]
                curr_tx = self.get_first_texture_slot(curr_mtl).texture

                if curr_tx.type == "IMAGE":
                    img_bname = get_bname(curr_tx.image.filepath)
                    img_fname = get_fname(curr_tx.image.filepath)
                    if img_fname.isnumeric():
                        # If the filename is numeric, use it as the
                        # texture index.
                        img_num = int(img_fname)
                        if img_num >= 0 and img_num <= 99999990:
                            # What if the user has two numeric image
                            # filenames that are the same number?
                            # i.e. 424242.jpg and 424242.png
                            if img_num not in mtl_texnums.values():
                                mtl_texnums[img_bname] = img_num
                            else:
                                mtl_texnums[img_bname] = curr_txnum
                                print(img_fname, "is already in use! Using",
                                      curr_txnum, "instead.")
                                num_textures += 1
                        else:
                            # If the number is too big,
                            # use the "default" value.
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

    def get_txinfo(self, mtl_texnums, as_comment=False):
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
            maxlen = max(map(len, mtl_texnums.keys()))
            tx_info += (
                "{:" + str(maxlen) +
                "} --> {!s:0>8}.mat\n").format(img_fname, texnum)
        return tx_info

    def get_children(self, obj):
        """Get a list of the object, and all of its exportable children.

        In order for a child object to be exportable, it must be:
        1. Parented to another valid LOD object or hardpoint.
        2. Named such that MAIN_LOD_RE or CHLD_LOD_RE matches its name.
        3. Visible in Blender's viewport."""
        # List containing an object and its children.
        objects = [obj]
        main_lod_used = False

        def is_valid_obj(obj, parent=None):
            if not (str(obj.parent) == str(parent) and obj.hide is False and
                    obj.type == "MESH"):
                return False

            if CHLD_LOD_RE.match(obj.name):
                return True
            elif MAIN_LOD_RE.match(obj.name):
                if main_lod_used is True:
                    return False
                main_lod_used = True
                return True

        def is_valid_hp(obj, parent=None):
            return (str(obj.parent) == str(parent) and obj.hide is False and
                    obj.type == "EMPTY" and HARDPOINT_RE.match(obj.name))

        # def info_for(obj):
        #     if is_valid_obj(obj):
        #         obj_match = CHLD_LOD_RE.match(obj.name)
        #         if obj_match:
        #             obj_bname = obj_match.group(1)
        #         else:
        #             obj_match = MAIN_LOD_RE.match(obj.name)
        #             obj_bname = self.modelname
        #
        #         return obj.name, obj_bname

        def children_of(parent_obj):
            childnames = []
            children = []
            parent_hps = []
            for obj in bpy.context.scene.objects:
                if is_valid_obj(obj, parent_obj):
                    obj_bname = CHLD_LOD_RE.match(obj.name)
                    if obj_bname:
                        obj_bname = obj_bname.group(1)
                    else:
                        obj_bname = self.modelname
                    if obj_bname not in childnames:
                        childnames.append(obj_bname)
                        children.append(obj)
                if is_valid_hp(obj, parent_obj) and obj not in parent_hps:
                    parent_hps.append(obj)

            for obj in bpy.context.scene.objects:
                for hp in parent_hps:
                    if is_valid_obj(obj, hp):
                        obj_bname = CHLD_LOD_RE.match(obj.name)
                        if obj_bname:
                            obj_bname = obj_bname.group(1)
                        else:
                            obj_bname = self.modelname
                        if obj_bname not in childnames:
                            childnames.append(obj_bname)
                            children.append(obj)

            if len(children) == 0:
                return children
            else:
                for obj in children:
                    children.extend(children_of(obj))

                return children

        objects.extend(children_of(obj))

        # import code
        # code.interact(banner="Entering REPL (L721).", local=locals())

        return objects

    def hierarchy_str_for(self, obj):
        """Get the export filename for the object.

        This function should be called after objects have been selected for
        export."""
        def parents_of(obj):
            if (obj.parent is not None and obj.parent.type == "MESH" and
                (MAIN_LOD_RE.match(obj.parent.name) or
                    CHLD_LOD_RE.match(obj.parent.name))
                    and obj.parent.hide is False):
                return [obj].extend(parents_of(obj.parent))
            elif (obj.parent is not None and obj.parent.type == "EMPTY" and
                  HARDPOINT_RE.match(obj.parent.name) and
                    obj.parent.hide is False):
                return [obj].extend(parents_of(obj.parent.parent))
            else:
                return [obj]

        def name_of(obj):
            if obj is not None:
                if MAIN_LOD_RE.match(obj.name) or CHLD_LOD_RE.match(obj.name):
                    return self.modelname

        if obj.parent is not None:
            hierarchy = parents_of(obj)
            return "_".join(reversed(map(lambda o: o.name, hierarchy)))
        else:
            return obj.name


class IFFExporter(ExportBackend):

    def export(self):
        """
        Export .iff files from the Blender scene.
        The model is exported as an .iff file, which can be used in
        Wing Commander: Prophecy/Secret Ops.

        Preconditions for a model to be exported:
        1. It must be named according to MAIN_LOD_RE or CHLD_LOD_RE
        2. All of its LODs must be Blender mesh objects.
        3. It must have a LOD 0
        4. All LODs that are to be exported, especially LOD 0, must be visible
           in Blender's viewport.
        """

        # Aliases to long function names
        # Filename without extension
        get_fname = bpy.path.display_name_from_filepath

        # Get directory path of output file, plus filename without extension
        modeldir = self.filepath[:self.filepath.rfind(dirsep)]
        self.modelname = get_fname(self.filepath)

        managers = []
        main_lod_used = False
        used_names = set()

        if self.export_active_only:
            # TODO: Traverse object hierarchy and assign export filenames from
            # here.
            if bpy.context.active_object is None:
                raise TypeError("You must have an object selected to export "
                                "only the active object!")

            # Traversing hierarchy here will allow the object export filename
            # to be set, as well as removing the need for traversing the
            # hierarchy in ModelManager.setup(). It's more efficient overall.

            active_hierarchy = self.get_children(bpy.context.active_object)

            for hobj in active_hierarchy:
                cur_manager = ModelManager(
                    "", hobj.name, self.use_facetex, self.drang_increment,
                    self.generate_bsp, bpy.context.scene.name)
                cur_manager.exp_fname = hierarchy_str_for(hobj)
                managers.append(cur_manager)
        else:
            for obj in bpy.context.scene.objects:
                if obj.parent is None and not obj.hide:
                    if MAIN_LOD_RE.match(obj.name) and not main_lod_used:
                        managers.append(ModelManager(
                            self.modelname, obj.name, self.use_facetex,
                            self.drang_increment, self.generate_bsp,
                            bpy.context.scene.name
                        ))
                        main_lod_used = True
                        warnings.warn("detail-x LOD naming scheme is "
                                      "deprecated.", DeprecationWarning)
                    else:
                        obj_match = CHLD_LOD_RE.match(obj.name)
                        if obj_match.group(1) not in used_names:
                            managers.append(ModelManager(
                                self.modelname, obj.name, self.use_facetex,
                                self.drang_increment, self.generate_bsp,
                                bpy.context.scene.name
                            ))
                            used_names.add(obj_match.group(1))

        for manager in managers:
            manager.setup()


class XMFExporter(ExportBackend):

    def export(self):
        """
        Export a .pas file from the Blender scene.
        The model is exported as an XMF (IFF source) file that can be compiled
        by WCPPascal into a WCP/SO format mesh iff file.

        Defunct as of commit 64f9f39, but may still be useful for debugging if
        the need arises.
        """

        # Aliases to long function names
        get_bname = bpy.path.basename  # Filename with extension

        # Get LOD data and number of LODs
        lod_data = self.get_lod_data()
        if type(lod_data) == tuple:  # tuple means error
            return lod_data
        num_lods = lod_data["num_lods"]

        # Get the hardpoints
        hardpoints = self.get_hardpoints()

        # Get filename w/o extension
        filename = bpy.path.display_name_from_filepath(self.filepath)

        # Get texture indices for each material
        mtl_texnums = self.get_materials(lod_data)

        outfile = open(self.filepath, 'w', encoding='utf-8')
        # IFF source file header. If this is not the first line,
        # the file will not compile.
        print('IFF "', filename, '.iff"', '\n',
              sep="", file=outfile)

        print(self.get_txinfo(mtl_texnums, True), file=outfile)

        print('{', '\n',
              ' ' * 2, 'FORM "DETA"', '\n',
              ' ' * 2, '{', '\n',
              ' ' * 4, 'CHUNK "RANG"', '\n',
              ' ' * 4, '{', '\n',
              ' ' * 6, 'float 0.0', '\n',
              ' ' * 6, 'float 400.0', '\n',
              ' ' * 6, 'float 800.0', '\n',
              ' ' * 4, '}', '\n',
              ' ' * 4, 'FORM "MESH"', '\n',
              ' ' * 4, '{', '\n',
              sep='', end='', file=outfile)
        for lod in range(num_lods):
            bl_mesh = lod_data["LOD-" + str(lod)].to_mesh(
                bpy.context.scene, self.apply_modifiers, "PREVIEW")

            bl_mesh.transform(lod_data["LOD-" + str(lod)].matrix_local)
            if self.wc_orientation_matrix is not None:
                bl_mesh.transform(self.wc_orientation_matrix)

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

            # Get the FORM name for this LOD
            lod_num = str(lod).zfill(4)
            print(
                ' ' * 6, 'FORM "', lod_num, '"', '\n',
                ' ' * 6, '{', '\n',
                ' ' * 8, 'FORM "MESH"', '\n',
                ' ' * 8, '{', '\n',
                ' ' * 10, 'FORM "0012"', '\n',  # Mesh format version number
                ' ' * 10, '{', '\n',
                ' ' * 12, 'CHUNK "NAME"', '\n',
                ' ' * 12, '{', '\n',
                ' ' * 14, 'cstring "', filename, '"', '\n',
                sep='', end='', file=outfile)

            # Alias to format method of format string. The format string
            # is being used for nothing more than formatting output values,
            # so I figured I might as well do it this way, plus, it makes
            # code lines shorter.
            lfmt = "long {}\n".format
            ffmt = "float {:.6f}\n".format

            # Vertices
            print(' ' * 12, '}', '\n',
                  ' ' * 12, 'CHUNK "VERT"', '\n',
                  ' ' * 12, '{',
                  sep='', file=outfile)

            for v in bl_mesh.vertices:
                vx, vy, vz = v.co[:]
                print(' ' * 14, ffmt(-vx),  # Vertex X
                      ' ' * 14, ffmt(vy),  # Vertex Y
                      ' ' * 14, ffmt(vz),  # Vertex Z
                      sep='', file=outfile)

            # Normals
            print(' ' * 12, '}', '\n',
                  ' ' * 12, 'CHUNK "VTNM"', '\n',
                  ' ' * 12, '{',
                  sep="", file=outfile)

            for n in unique_normals:
                vx, vy, vz = n[:]
                print(' ' * 14, ffmt(-vx),  # Normal X
                      ' ' * 14, ffmt(vy),  # Normal Y
                      ' ' * 14, ffmt(vz),  # Normal Z
                      sep='', file=outfile)

            # Vertices on each face
            print(' ' * 12, '}', '\n',
                  ' ' * 12, 'CHUNK "FVRT"', '\n',
                  ' ' * 12, '{',
                  sep='', file=outfile)

            fnrm_idx = 0
            uv_map = bl_mesh.tessface_uv_textures.active.data
            for f, u in zip(bl_mesh.tessfaces, uv_map):
                for v, uv in zip(reversed(f.vertices), reversed(u.uv)):
                    if f.use_smooth:
                        # If smoothing is enabled, use the vertex normal
                        vtnm_idx = vnrmrefs[v]
                    else:
                        # Otherwise, use the face normal
                        vtnm_idx = fnrmrefs[fnrm_idx]
                    vert_idx = v
                    uvX, uvY = uv
                    print(' ' * 14, lfmt(vert_idx),  # Reference to VERT
                          ' ' * 14, lfmt(vtnm_idx),  # Reference to VTNM
                          ' ' * 14, ffmt(uvX),
                          # 1 - uvY allows textures to be converted without
                          # the modder having to vertically flip them.
                          ' ' * 14, ffmt(1 - uvY),
                          sep='', file=outfile)
                fnrm_idx += 1

            # Faces
            print(' ' * 12, '}', '\n',
                  ' ' * 12, 'CHUNK "FACE"', '\n',
                  ' ' * 12, '{',
                  sep='', file=outfile)

            fvrt_idx = 0
            for cur_face_idx, cur_face in enumerate(bl_mesh.tessfaces):
                light_flags = 0

                if self.use_facetex:
                    active_idx = None
                    mesh_uvtex = bl_mesh.tessface_uv_textures
                    for idx, texmap in enumerate(mesh_uvtex):
                        if texmap.active:
                            active_idx = idx
                            break
                    facetex = mesh_uvtex[active_idx].data[cur_face_idx]
                    matfilename = get_bname(facetex.image.filepath)
                    texnum = mtl_texnums[matfilename]
                else:
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
                            print("Cannot convert", facemtl["light_flags"],
                                  "to an integer value!")

                num_verts = len(cur_face.vertices)

                vtnm_idx = fnrmrefs[cur_face_idx]

                # Vertex coordinates and normals are needed
                # in order to calculate the D-Plane.
                first_vert = bl_mesh.vertices[cur_face.vertices[0]].co
                face_nrm = cur_face.normal
                dplane = self.calc_dplane(first_vert, face_nrm)

                print(
                    ' ' * 14, lfmt(vtnm_idx),     # Face normal
                    ' ' * 14, ffmt(dplane),       # D-Plane
                    ' ' * 14, lfmt(texnum),       # Texture number
                    ' ' * 14, lfmt(fvrt_idx),     # Index of face's first FVRT
                    ' ' * 14, lfmt(num_verts),    # Number of vertices
                    ' ' * 14, lfmt(light_flags),  # Lighting flags
                    ' ' * 14, lfmt('$7F0096FF'),  # Unknown
                    sep='', file=outfile
                )
                fvrt_idx += num_verts

            # Location, radius metadata for this LOD
            loc = lod_data["LOD-" + str(lod)].location
            radius = self.calc_radius(lod_data["LOD-" + str(lod)].dimensions)

            # Center of object
            print('            }', '\n',
                  '            CHUNK "CNTR"', '\n',
                  '            {', '\n',
                  ' ' * 14, ffmt(loc[0]),  # Center X
                  ' ' * 14, ffmt(loc[1]),  # Center Y
                  ' ' * 14, ffmt(loc[2]),  # Center Z
                  '            }', '\n',

                  # Radius. Used by object camera
                  ' ' * 12, 'CHUNK "RADI"', '\n',
                  ' ' * 12, '{', '\n',
                  ' ' * 14, ffmt(radius),
                  ' ' * 12, '}', '\n',
                  ' ' * 10, '}', '\n',
                  ' ' * 8, '}', '\n',
                  ' ' * 6, '}', '\n',
                  sep='', file=outfile)
        print(' ' * 4, '}', '\n',
              ' ' * 4, 'FORM "HARD"', '\n',
              ' ' * 4, '{',
              sep='', file=outfile)

        # Hardpoints - These will be created from empties prefixed with "hp-"
        for h in hardpoints:
            print(' ' * 6, 'CHUNK "HARD"', '\n',
                  ' ' * 6, '{', '\n',
                  ' ' * 8, ffmt(h["rot_matrix"][0][0]),
                  ' ' * 8, ffmt(h["rot_matrix"][0][1]),
                  ' ' * 8, ffmt(h["rot_matrix"][0][2]),
                  ' ' * 8, ffmt(h["x"]),     # Hardpoint X
                  ' ' * 8, ffmt(h["rot_matrix"][1][0]),
                  ' ' * 8, ffmt(h["rot_matrix"][1][1]),
                  ' ' * 8, ffmt(h["rot_matrix"][1][2]),
                  ' ' * 8, ffmt(h["y"]),     # Hardpoint Y
                  ' ' * 8, ffmt(h["rot_matrix"][2][0]),
                  ' ' * 8, ffmt(h["rot_matrix"][2][1]),
                  ' ' * 8, ffmt(h["rot_matrix"][2][2]),
                  ' ' * 8, ffmt(h["z"]),     # Hardpoint Z
                  ' ' * 8, 'cstring "', h["name"], '"', '\n',  # Hardpoint name
                  ' ' * 6, '}',
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
                radius = self.calc_radius(lod_data["LOD-0"].dimensions)
        except KeyError:
            print("collsphr object not found")
            loc = lod_data["LOD-0"].location
            radius = self.calc_radius(lod_data["LOD-0"].dimensions)
        print(' ' * 4, '}', '\n',
              ' ' * 4, 'FORM "COLL"', '\n',      # Collision info
              ' ' * 4, '{', '\n',
              ' ' * 6, 'CHUNK "SPHR"', '\n',   # Collision Sphere
              ' ' * 6, '{', '\n',
              ' ' * 8, ffmt(loc[0]),   # Center X
              ' ' * 8, ffmt(loc[1]),   # Center Y
              ' ' * 8, ffmt(loc[2]),   # Center Z
              ' ' * 8, ffmt(radius),   # Radius
              ' ' * 6, '}', '\n',
              ' ' * 4, '}', '\n',
              ' ' * 4, 'CHUNK "FAR "', '\n',
              ' ' * 4, '{', '\n',
              ' ' * 6, 'float 0.0', '\n',
              ' ' * 6, 'float 900000.0', '\n',
              ' ' * 4, '}', '\n',
              ' ' * 2, '}', '\n',
              '}', '\n',
              sep='', file=outfile)
        outfile.close()

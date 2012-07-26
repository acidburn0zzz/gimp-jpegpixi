#!/usr/bin/env python
# jpegpixi.py - a GIMP script to use jpegpixi
#
#   Copyright 2012 Aleksej
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from os import system
from gimpfu import *

# The grid spacing needed to match DCT blocks (to help user choose
# a less lossy position).
#
# Wikipedia says DCT blocks are 8x8.  It also says some lossless
# operations can be performed on MCU blocks, which are usually
# 16x16.  If it's only MCU and not DCT, it would be more
# convenient to use the MCU size here, but jpegpixi's man page
# says DCT.
REQUIRED_GRID_SPACING = (8, 8)


def python_pixi(timg, tdrawable, method, direction,
                max_selection_size, rename_method, fn_sufbase):
    have_selection = pdb.gimp_selection_bounds(timg)[0]

    grid_offset = pdb.gimp_image_grid_get_offset(timg)
    grid_spacing = pdb.gimp_image_grid_get_spacing(timg)

    if not have_selection:
        set_grid(timg)
        pdb.gimp_message("A selection is required.")
    elif not ((grid_offset, grid_spacing) ==
              ((0, 0), REQUIRED_GRID_SPACING)):
        pdb.gimp_message_set_handler(ERROR_CONSOLE)
        pdb.gimp_message(
            "Grid offset and spacing are not 0, 0 and %d, %d.  Fixing, but please retry." %
                REQUIRED_GRID_SPACING)
        set_grid(timg)

        return
    else:
        we_have_a_selection(timg, tdrawable, method, direction,
                            max_selection_size, fn_sufbase, rename_method)
        return



def we_have_a_selection(timg, tdrawable, method, direction,
                        max_selection_size, fn_sufbase, rename_method):

    x1, y1, sx, sy = rect_coords(pdb.gimp_selection_bounds(timg)[1:])
    selection_size = sx * sy
    if selection_size > max_selection_size:
        pdb.gimp_message_set_handler(ERROR_CONSOLE)
        pdb.gimp_message(
            "Selection is %d pixels, over %d.  Aborting for safety." %
                (selection_size, max_selection_size))
        return
    else:
        # source and target file names
        sfname = pdb.gimp_image_get_filename(timg)
        tfname = next_filename(sfname, rename_method, fn_sufbase,
                               (x1, y1, sx, sy))

        coord_string = "%i,%i,%i,%i" % (x1, y1, sx, sy)
        the_command = jpegpixi_cmd(sfname, tfname, coord_string,
                                   method, direction)

        print the_command

        system(the_command)

        # Load the new image in a new window.
        targetimg = pdb.file_jpeg_load(tfname, RUN_INTERACTIVE)
        gimp.Display(targetimg)
        tdrawable.flush()

        # Select the interpolated part in the new window.
        pdb.gimp_image_select_rectangle(
            targetimg, CHANNEL_OP_REPLACE, x1, y1, sx, sy)

        set_grid(targetimg)

        return


def set_grid(timg):
    """Sets grid parameters for convenient selection.  This only has
    effect on the specified image and does not affect the default values
    set in GIMP preferences.
    """
    pdb.gimp_image_grid_set_offset(timg, 0, 0) 
    pdb.gimp_image_grid_set_spacing(timg, REQUIRED_GRID_SPACING[0],
                                        REQUIRED_GRID_SPACING[1]) 


def next_filename(sfname, rename_method, fn_sufbase, coords):
    """Generates the target filename out of the source one and other
    data using the method specified.
    """    
    sfname_base, sfname_ext = sfname.rsplit('.', 1)

    if rename_method == 'rect_coords':
        id_from_coord_string = 'x'.join(map(lambda x: str(x), coords))
        tfname = (sfname_base + fn_sufbase + id_from_coord_string + "." +
            sfname_ext)
    elif rename_method == 'rect_coords_hex':
        id_from_coord_string = 'x'.join(map(lambda x: hex(x), coords))
        tfname = (sfname_base + fn_sufbase + id_from_coord_string + "." +
            sfname_ext)
    elif rename_method == 'incremental':
        tfname = next_filename_incremental(sfname_base, sfname_ext, fn_sufbase)
    else:
        # CropGUI method
        tfname = sfname_base + fn_sufbase + "." + sfname_ext

    return tfname


def next_filename_incremental(sfname_base, sfname_ext, fn_sufbase):
    """If the file name base ends in "-pixi<n>", makes it "-pixi<n+1>".  Adds
    "-pixi1" if there is no "-pixi".
    """
    (fn_presuf, fn_hopefully_sufbase,
        fn_hopefully_number) = sfname_base.rpartition(fn_sufbase)

    if fn_presuf == "":
        tfname = sfname_base + fn_sufbase + '1.' + sfname_ext
    else:
        fn_number = int(fn_hopefully_number)
        fn_number += 1
        tfname = fn_presuf + fn_sufbase + str(fn_number) + '.' + sfname_ext

    return tfname


def rect_coords(points_coords):
    """Takes coordinates of two angles of a rectangle, and replaces
    those of the second one with the rectangle's dimensions.
    """
    x1, y1, x2, y2 = points_coords
    sx = x2 - x1
    sy = y2 - y1
    return (x1, y1, sx, sy)


def jpegpixi_cmd(sfname, tfname, coord_string, method, direction):
    """Returns the shell command ready to execute."""
    progname = "jpegpixi"
    cmdl_opts = cmdl_method = "-m " + method
    cmdl_sfname = shellquote(sfname)
    cmdl_tfname = shellquote(tfname)
    cmdl_spec = direction + ':' + coord_string

    cmdl_total = [progname, cmdl_opts, cmdl_sfname, cmdl_tfname, cmdl_spec]
    
    return (' '.join(cmdl_total))


def shellquote(s):
    """Escapes file names for the shell."""
    return ("'" + s.replace("'", "'\\''") + "'")


register(
    "python_pixi",
    "Pixelize the selection using jpegpixi.",
    """Pixelize the selection using jpegpixi.  Makes GIMP serve as a GUI for jpegpixi.
    It calls jpegpixi on _the file_ by the name of the loaded image, not on the
    drawable in GIMP, so any unsaved changes will be ignored.
    """,
    "Aleksej",
    "Aleksej",
    "2012",
    "<Image>/Filters/Blur/_jpegpixi",
    "RGB*, GRAY*",
    [
        (PF_RADIO, 'method', 'Interpolation\n method', "li",
            (("average", "av"), ("linear", "li"), ("quadratic", "qu"),
                ("cubic", "cu"))),
        (PF_RADIO, 'direction', 'Direction', "2", (("2d", "2"),
            ("1d vertical", "v"), ("1d horizontal", "h"))),
        # Maximum selecton size, to prevent "out-of-memory" issues.
        (PF_SLIDER, 'max_selection_size', 'Max. sel. size', 10000,
            (10000, 100000, 100)),
        (PF_RADIO, 'rename_method', 'Target file\nnaming', 'rect_coords',
            (('Coords+dims', 'rect_coords'),
                ('add suffix (like CropGUI)', 'cropgui'),
                ("increment number at suffix", "incremental"))),
        (PF_STRING, 'fn_sufbase', 'Filename\nsuffix base', '-pixi')
    ],
    [],
    python_pixi)

main()


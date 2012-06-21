#!/usr/bin/python -tt

from os import system
from gimpfu import *

def python_pixi(timg, tdrawable, method, direction,
                max_selection_size, rename_method, fn_sufbase):
    have_selection = pdb.gimp_selection_bounds(timg)[0]

    # The grid spacing needed to match DCT blocks (to choose a less
    # lossy position).
    # Wikipedia says DCT blocks are 8x8.  It also says some lossless
    # operations can be performed on MCU blocks, which are usually
    # 16x16.  If it's only MCU and not DCT, it would be more
    # convenient to use the MCU size here, but jpegpixi's man page
    # says DCT.
    required_grid_spacing = (8, 8)
    grid_offset = pdb.gimp_image_grid_get_offset(timg)
    grid_spacing = pdb.gimp_image_grid_get_spacing(timg)

    if not have_selection:
        pdb.gimp_message("A selection is required.")
    elif not ((grid_offset, grid_spacing) ==
              ((0, 0), (required_grid_spacing[0], required_grid_spacing[1]))):
        pdb.gimp_message_set_handler(ERROR_CONSOLE)
        pdb.gimp_message(
            "Grid offset and spacing are not 0, 0 and %d, %d.  Fixing, but please retry." %
                (required_grid_spacing[0], required_grid_spacing[1]))
        pdb.gimp_image_grid_set_offset(timg, 0, 0) 
        pdb.gimp_image_grid_set_spacing(timg, required_grid_spacing[0],
                                        required_grid_spacing[1]) 
        return
    else:
        we_have_a_selection(timg, tdrawable, method, direction,
                            max_selection_size, fn_sufbase, rename_method)


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
        tfname = next_filename(sfname, rename_method, fn_sufbase, (x1, y1, sx, sy))

        coord_string = "%i,%i,%i,%i" % (x1, y1, sx, sy)
        the_command = jpegpixi_cmd(sfname, tfname, coord_string,
                                   method, direction)

        print the_command

        system(the_command)

        # Load the new image in a new window.
        targetimg = pdb.file_jpeg_load(tfname, RUN_INTERACTIVE)
        gimp.Display(targetimg)
        tdrawable.flush()
        pdb.gimp_image_select_rectangle(
            targetimg, CHANNEL_OP_REPLACE, x1, y1, sx, sy)
        # XXX I suppose the grid is the same as the one in the original image.
        return


# Maybe this function should simply generate the suffix from the coordinates,
# and add it like cropgui does  It could also simply add "-pixi" every time,
# but since existing files are overwritten.

def next_filename(sfname, rename_method, fn_sufbase, coords):
    sfname_base, sfname_ext = sfname.rsplit('.', 2)


    if rename_method == 'rect_coords':
        id_from_coord_string = 'x'.join(map(lambda x: str(x), coords))
        tfname = sfname_base + fn_sufbase + id_from_coord_string + "." + sfname_ext
    elif rename_method == 'rect_coords_hex':
        id_from_coord_string = 'x'.join(map(lambda x: hex(x), coords))
        tfname = sfname_base + fn_sufbase + id_from_coord_string + "." + sfname_ext
    elif rename_method == 'incremental':
        tfname = next_filename_incremental(sfname_base, sfname_ext, fn_sufbase)
    else:
        # CropGUI method
        tfname = sfname_base + fn_sufbase + "." + sfname_ext

    return tfname

def next_filename_incremental(sfname_base, sfname_ext, fn_sufbase):

    fn_presuf, fn_hopefully_sufbase, fn_hopefully_number = sfname_base.rpartition(
        fn_sufbase)

    if fn_presuf == "":
        tfname = sfname_base + fn_sufbase + '1.' + sfname_ext
    else:
        fn_number = int(fn_hopefully_number)
        fn_number += 1
        tfname = fn_presuf + fn_sufbase + str(fn_number) + '.' + sfname_ext

    return tfname


# Takes coordinates of two angles of a rectangle, and replaces those of the
# second one with the rectangle's dimensions.
def rect_coords(points_coords):
    x1, y1, x2, y2 = points_coords
    sx = x2 - x1
    sy = y2 - y1
    return (x1, y1, sx, sy)


def jpegpixi_cmd(sfname, tfname, coord_string, method, direction):
    return ("jpegpixi -m %s %s %s %s:%s" %
        (method, shellquote(sfname), shellquote(tfname), direction,
        coord_string))


def shellquote(s):
    return "'" + s.replace("'", "'\\''") + "'"


register(
    "python_pixi",
    "pixelize the selection using jpegpixi",
    "pixelize the selection using jpegpixi",
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
        (PF_RADIO, 'rename_method', 'Target file naming', 'rect_coords',
            (('Coords+dims', 'rect_coords'),
                ('add suffix (like CropGUI)', 'cropgui'),
                ("increment number at suffix", "incremental"))),
        (PF_STRING, 'fn_sufbase', 'Filename suffix base', '-pixi')
    ],
    [],
    python_pixi)

main()


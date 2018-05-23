"""Digital Elevation Map (DEM) downloading/stitching/upsampling
"""
import numpy as np
from scipy.interpolate import RegularGridInterpolator

from insar import sario


def upsample_dem(dem_img, rate=3):
    """Interpolates a DEM to higher resolution for better InSAR quality


    Args:
        dem_img: numpy.ndarray (int16)
        rate: int, default = 3

    Returns:
        numpy.ndarray (int16): original dem_img upsampled by `rate`. Needs
            to return same type since downstream scripts expect int16 DEMs

    """

    s1, s2 = dem_img.shape
    # TODO: figure out whether makeDEM.m really needs to form using
    # points 1:size and then interpolate with points 0:size
    orig_points = (np.arange(1, s1 + 1), np.arange(1, s2 + 1))
    rgi = RegularGridInterpolator(points=orig_points, values=dem_img)

    # Make a grid from 0 to (size-1) inclusive, in both directions
    # 1j used to say "make s1*rate number of points exactly"
    numx = 1 + (s1 - 1) * rate
    numy = 1 + (s2 - 1) * rate
    X, Y = np.mgrid[1:s1:numx * 1j, 1:s2:numy * 1j]

    # new_points will be a 2xN matrix, N=(numx*numy)
    new_points = np.vstack([X.ravel(), Y.ravel()])

    # rgi expects Nx2 as input, and will output as a 1D vector
    return rgi(new_points.T).reshape(numx, numy).round().astype(dem_img.dtype)


def mosaic_dem(d1, d2):
    D = np.concatenate((d1, d2), axis=1)
    nrows, ncols = d1.shape
    D = np.delete(D, nrows, axis=1)
    return D


def upsample_dem_rsc(filepath, rate):
    """Creates a new .dem.rsc file for upsampled version

    Adjusts the FILE_LENGTH, WIDTH, X_STEP, Y_STEP for new rate

    Args:
        filepath (str) location of .dem.rsc file
        rate (int)

    Returns:
        str: file same as original with upsample adjusted numbers

    """
    outstring = ""
    rsc_data = sario.load_dem_rsc(filepath)
    for field, value in rsc_data.items():
        # Files seemed to be left justified with 13 spaces? Not sure why 13
        if field in ('width', 'file_length'):
            value *= rate
            outstring += "{field:<13s}{val}\n".format(field=field.upper(), val=value)
        elif field in ('x_step', 'y_step'):
            value /= rate
            # Also give step floats proper sig figs to not output scientific notation
            outstring += "{field:<13s}{val:0.12f}\n".format(field=field.upper(), val=value)
        else:
            outstring += "{field:<13s}{val}\n".format(field=field.upper(), val=value)

    return outstring


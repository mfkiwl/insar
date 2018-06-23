"""Functions for performing time series analysis of unwrapped interferograms

files in the igrams folder:
    geolist, intlist, sbas_list
scott@lidar igrams]$ head geolist
../S1A_IW_SLC__1SDV_20180420T043026_20180420T043054_021546_025211_81BE.SAFE.geo
../S1A_IW_SLC__1SDV_20180502T043026_20180502T043054_021721_025793_5C18.SAFE.geo
[scott@lidar igrams]$ head sbas_list
../S1A_IW_SLC__1SDV_20180420T043026_20180420T043054_021546_025211_81BE.SAFE.geo ../S1A_IW_SLC__1SDV_20180502T043026_20180502T043054_021721_025793_5C18.SAFE.geo 12.0   -16.733327776024169
[scott@lidar igrams]$ head intlist
20180420_20180502.int

"""
import os
import datetime
import numpy as np
import matplotlib.pyplot as plt

from insar.parsers import Sentinel
from insar import sario
from insar.log import get_log, log_runtime

SENTINEL_WAVELENGTH = 5.5465763  # cm
PHASE_TO_CM = SENTINEL_WAVELENGTH / (-4 * np.pi)

logger = get_log()


def read_geolist(filepath="./geolist"):
    """Reads in the list of .geo files used, in time order

    Args:
        filepath (str): path to the intlist file

    Returns:
        list[date]: the parse dates of each .geo used, in date order

    """
    with open(filepath) as f:
        geolist = [os.path.split(geoname)[1] for geoname in f.read().splitlines()]
    return sorted([Sentinel(geo).start_time().date() for geo in geolist])


def read_intlist(filepath="./intlist", parse=True):
    """Reads the list of igrams to return dates of images as a tuple

    Args:
        filepath (str): path to the intlist file
        parse (bool): output the intlist as parsed datetime tuples

    Returns:
        tuple(date, date) of master, slave dates for all igrams (if parse=True)
            if parse=False: returns list[str], filenames of the igrams

    """

    def _parse(datestr):
        return datetime.datetime.strptime(datestr, "%Y%m%d").date()

    with open(filepath) as f:
        intlist = f.read().splitlines()

    if parse:
        intlist = [intname.strip('.int').split('_') for intname in intlist]
        return [(_parse(master), _parse(slave)) for master, slave in intlist]
    else:
        dirname = os.path.dirname(filepath)
        return [os.path.join(dirname, igram) for igram in intlist]


def build_A_matrix(geolist, intlist):
    """Takes the list of igram dates and builds the SBAS A matrix

    Args:
        geolist (list[date]): datetimes of the .geo acquisitions
        intlist (list[tuple(date, date)])

    Returns:
        np.array 2D: the incident-like matrix from the SBAS paper: A*phi = dphi
            Each row corresponds to an igram, each column to a .geo
            value will be -1 on the early (slave) igrams, +1 on later (master)
    """
    # We take the first .geo to be time 0, leave out of matrix
    # Match on date (not time) to find indices
    geolist = geolist[1:]
    M = len(intlist)  # Number of igrams, number of rows
    N = len(geolist)
    A = np.zeros((M, N))
    for j in range(M):
        early_igram, late_igram = intlist[j]

        try:
            idx_early = geolist.index(early_igram)
            A[j, idx_early] = -1
        except ValueError:  # The first SLC will not be in the matrix
            pass

        idx_late = geolist.index(late_igram)
        A[j, idx_late] = 1

    return A


def find_time_diffs(geolist):
    """Finds the number of days between successive .geo files

    Args:
        geolist (list[date]): dates of the .geo SAR acquisitions

    Returns:
        np.array: days between each datetime in geolist
            dtype=int, length is a len(geolist) - 1"""
    return np.array([difference.days for difference in np.diff(geolist)])


def build_B_matrix(geolist, intlist):
    """Takes the list of igram dates and builds the SBAS B (velocity coeff) matrix

    Args:
        geolist (list[date]): dates of the .geo SAR acquisitions
        intlist (list[tuple(date, date)])

    Returns:
        np.array: 2D array of the velocity coefficient matrix from the SBAS paper:
                Bv = dphi
            Each row corresponds to an igram, each column to a .geo
            value will be t_k+1 - t_k for columns after the -1 in A,
            up to and including the +1 entry
    """
    timediffs = find_time_diffs(geolist)

    A = build_A_matrix(geolist, intlist)
    B = np.zeros_like(A)

    for j, row in enumerate(A):
        # if no -1 entry, start at index 0. Otherwise, add 1 so exclude the -1 index
        start_idx = list(row).index(-1) + 1 if (-1 in row) else 0
        # End index is inclusive of the +1
        end_idx = np.where(row == 1)[0][0] + 1  # +1 will always exist in row

        # Now only fill in the time diffs in the range from the early igram index
        # to the later igram index
        B[j][start_idx:end_idx] = timediffs[start_idx:end_idx]

    return B


def read_unw_stack(igram_path, ref_row, ref_col):
    """Reads all unwrapped phase .unw files into unw_stack

    Uses ref_row, ref_col as the normalizing point (subtracts
        that pixels value from all others in each .unw file)

    Args:
        igram_path (str): path to the directory containing `intlist`,
            the .int filenames, the .unw files, and the dem.rsc file
        ref_row (int): row index of the reference pixel to subtract
        ref_col (int): col index of the reference pixel to subtract

    Returns:
        ndarray: 3D array of each unw file stacked along axis=3

    """

    def _allocate_stack(igram_path, num_ints):
        # Get igram file size data to pre-allocate space for 3D unw stack
        rsc_path = os.path.join(igram_path, 'dem.rsc')
        rsc_data = sario.load_file(rsc_path)
        rows = rsc_data['FILE_LENGTH']
        cols = rsc_data['WIDTH']
        return np.empty((rows, cols, num_ints), dtype='float32')

    # row 283, col 493 looks like a good test
    intlist_path = os.path.join(igram_path, 'intlist')
    igram_files = read_intlist(intlist_path, parse=False)
    num_ints = len(igram_files)

    unw_stack = _allocate_stack(igram_path, num_ints)

    for idx, igram_file in enumerate(igram_files):
        unw_file = igram_file.replace('.int', '.unw')
        cur_unw = sario.load_file(unw_file)
        try:
            unw_stack[:, :, idx] = cur_unw - cur_unw[ref_row, ref_col]
        except IndexError:
            logger.error("Reference pixel (%s, %s) is out of bounds for unw shape %s", ref_row,
                         ref_col, unw_stack.shape[:2])
            raise
    return unw_stack


def display_stack(array_stack, pause_time=0.05):
    """Runs a matplotlib loop to show each image in a 3D stack

    Args:
        array_stack (ndarray): 3D np.ndarray
        pause_time (float): time between images

    Returns:
        None

    Notes: may need this
        https://github.com/matplotlib/matplotlib/issues/7759/#issuecomment-271110279
    """
    fig, ax = plt.subplots()

    for idx in range(array_stack.shape[2]):
        ax.imshow(array_stack[..., idx])
        plt.show()
        plt.pause(pause_time)


def invert_sbas(delta_phis, timediffs, B):
    """Performs and SBAS inversion on each pixel of unw_stack to find deformation

    Args:
        delta_phis (ndarray): 1D array of unwrapped phases (delta phis)
            comes from 1 pixel of read_unw_stack along 3rd axis
        B (ndarray): output of build_B_matrix for current set of igrams
        timediffs (np.array): dtype=int, days between each SAR acquisitions
            length will be equal to B.shape[1], 1 less than num SAR acquisitions

    return

    """
    assert B.shape[1] == len(timediffs)

    # Velocity will be result of the inversion
    velocity_array, _, rank_B, sing_vals_B = np.linalg.lstsq(B, delta_phis, rcond=None)
    # velocity array entries: v_j = (phi_j - phi_j-1)/(t_j - t_j-1)
    if velocity_array.ndim == 1:
        velocity_array = np.expand_dims(velocity_array, axis=-1)

    # Now integrate to get back to phases
    # multiple each column of vel array: each col is a separate solution
    phi_diffs = timediffs.reshape((-1, 1)) * velocity_array

    # Now the final phase results are the cumulative sum of delta phis
    phi_arr = np.cumsum(phi_diffs, axis=0)
    # Add 0 as first entry of phase array to match geolist length on each col
    phi_arr = np.insert(phi_arr, 0, 0, axis=0)

    return velocity_array, phi_arr


def _prep_columns(stacked):
    """Takes a 3D array, makes vectors along the 3D axes into cols

    Args:
        stacked (ndarray): 3D array, each [:, :, idx] is an slice

    Returns:
        ndarray: a 2D array where each of the stacked[i,j,:] is
            now a column

    Example:
        >>> a = np.zeros((3, 3, 2))
        >>> a[:, :, 0] = np.array([[0, 1, 2,],[3, 4, 5,], [6, 7, 8,]])
        >>> a[:, :, 1] = np.array([[9, 10, 11,], [12, 13, 14], [15, 16, 17,]])
        >>> print(_prep_columns(a))
        [[ 0.  3.  6.  1.  4.  7.  2.  5.  8.]
         [ 9. 12. 15. 10. 13. 16. 11. 14. 17.]]
    """
    assert len(stacked.shape) == 3, "Must be a 3D ndarray"
    num_stacks = stacked.shape[2]
    return stacked.T.reshape((num_stacks, -1))


@log_runtime
def run_inversion(igram_path, reference=(483, 493), verbose=False):
    if verbose:
        logger.setLevel(10)  # DEBUG

    intlist_path = os.path.join(igram_path, 'intlist')
    geolist_path = os.path.join(igram_path, 'geolist')

    intlist = read_intlist(filepath=intlist_path)
    geolist = read_geolist(filepath=geolist_path)

    logger.debug("Reading stack")
    unw_stack = read_unw_stack(igram_path, *reference)
    logger.debug("Reading stack complete")

    # Prepare B matrix and timediffs used for each pixel inversion
    B = build_B_matrix(geolist, intlist)
    timediffs = find_time_diffs(geolist)

    phi_columns = _prep_columns(unw_stack)
    varr, phi_arr = invert_sbas(phi_columns, timediffs, B)
    deformation = PHASE_TO_CM * phi_arr

    return geolist, phi_arr, deformation, varr

import numpy as np

def mask_signal(signal, epochs):
    mask = np.zeros_like(signal)
    for lb, ub in epochs:
        mask[..., lb:ub] = True
    return np.ma.masked_array(signal, mask=mask)


def ts(TTL):
    '''
    Return nonzero indices (e.g. rising or falling) edges of the TTL
    '''
    return np.flatnonzero(TTL)

def edge_rising(TTL, assume_zero=False):
    '''
    Return indices of rising edges

    Parameters
    ----------
    TTL : 1D array
        Array to be evaluated as a logical.  A logical True is treated as a
        "high" in TTL parlance.
    assume_zero : bool
        For edge-cases where the first value is high, should we assume that this
        represents a rising edge (i.e. the sample immediately prior was low)?
    '''
    if assume_zero:
        return np.diff(np.r_[0, TTL.astype('i')]) == 1
    else:
        return np.r_[0, np.diff(TTL.astype('i'))] == 1

def edge_falling(TTL, assume_zero=False):
    '''
    Return indices of falling edges

    Parameters
    ----------
    TTL : 1D array
        Array to be evaluated as a logical.  A logical True is treated as a
        "high" in TTL parlance.
    assume_zero : bool
        For edge-cases where the final value is high, should we assume that this
        represents a falling edge (i.e. the sample immediately following would
        be low)
    '''
    if assume_zero:
        return np.diff(np.r_[TTL.astype('i'), 0]) == -1
    else:
        return np.r_[0, np.diff(TTL.astype('i'))] == -1

def epochs(x, pad=0, smooth=True, assume_zero=False):
    '''
    Identify start and end indices where the TTL goes high

    Parameters
    ----------
    x : 1D array
        Array to be evaluated as a logical.  A logical True is treated as a
        "high" in TTL parlance.
    pad : {two-tuple, int}
        Expand epoch boundaries by the requested number of indices.  Will not
        expand epoch boundaries beyond the edges of the input.  If padding is a
        two-tuple, indicates how much to pad lower and upper edge by.
    assume_zero : bool
        For edge-cases where the inital or final value is high, should we assume
        that these reflect an epoch boundary?

    Returns
    -------
    2D array

    Examples
    --------
    >>> x = np.zeros(10)

    Boundary conditions 
    -------------------
    >>> x = np.zeros(10)
    >>> epochs(x)
    array([], shape=(0, 2), dtype=float64)

    >>> x[-1] = 1
    >>> print epochs(x)
    [[ 9 10]]

    >>> x[0] = 1
    >>> print epochs(x)
    [[ 0  1]
     [ 9 10]]

    >>> x = np.ones(10)
    >>> print epochs(x)
    []

    >>> x = np.ones(10)
    >>> print epochs(x, assume_zero=True)
    [[ 0 10]]
    '''
    start = ts(edge_rising(x, assume_zero=assume_zero))
    end = ts(edge_falling(x, assume_zero=assume_zero))

    # Handle various boundary conditions where some sort of task-related
    # activity is registered at very beginning or end of experiment.
    if len(end) == 0 and len(start) == 0:
        return np.array([]).reshape((0, 2))
    elif len(end) == 0 and len(start) == 1:
        end = np.r_[end, len(x)]
    elif len(end) == 1 and len(start) == 0:
        start = np.r_[0, start]

    if end[0] < start[0]:
        start = np.r_[0, start]
    if end[-1] < start[-1]:
        end = np.r_[end, len(x)]

    try:
        start_pad, end_pad = pad
        start = start-start_pad
        end = end+end_pad
    except:
        start = start-pad
        end = end+pad

    epochs = np.c_[start, end]
    epochs = np.clip(epochs, 0, len(x))
    
    if smooth:
        epochs = smooth_epochs(epochs)

    return epochs


def pad_epochs(epochs, pad):
    '''
    Identify start and end indices where the TTL goes high

    Parameters
    ----------
    epochs : 2D array
        List of epochs
    pad : {two-tuple, int}
        Expand epoch boundaries by the requested number of indices.  Will not
        expand epoch boundaries beyond the edges of the input.  If padding is a
        two-tuple, indicates how much to pad lower and upper edge by.

    Returns
    -------
    2D array
    '''

    epochs = epochs.copy()
    try:
        start_pad, end_pad = pad
    except:
        start_pad, end_pad = pad, pad
    epochs[:,0] -= start_pad
    epochs[:,1] += end_pad
    return epochs


def debounce_epochs(epochs, pad):
    '''
    Detect spurious fluctuations in the TTL and remove these

    Parameters
    ----------
    epochs : 2D array
        List of epochs
    pad : {two-tuple, int}

    Returns
    -------
    2D array
    '''
    
    # Remove spurious fluctuations that go high->low->high
    epochs = pad_epochs(epochs, pad)
    epochs = smooth_epochs(epochs)
    epochs = pad_epochs(epochs, -pad)

    # Remove spurious fluctuations that go low->high->low
    d_epochs = np.diff(epochs, axis=1).ravel()
    epochs = epochs[d_epochs >= pad*2]

    return epochs


def smooth_epochs(epochs):
    '''
    Given a 2D array of epochs in the format [[start time, end time], ...],
    identify and remove all overlapping epochs such that::

        [ epoch   ]        [ epoch ] 
            [ epoch ]

    Will become::

        [ epoch     ]      [ epoch ]

    Epochs do not need to be ordered when provided; however, they will be
    returned ordered.
    '''
    if len(epochs) == 0:
        return epochs
    epochs = np.asarray(epochs)
    epochs.sort(axis=0)
    i = 0
    n = len(epochs)
    smoothed = []
    while i < n:
        lb, ub = epochs[i]
        i += 1
        while (i < n) and (ub >= epochs[i,0]):
            ub = epochs[i,1]
            i += 1
        smoothed.append((lb, ub))
    return np.array(smoothed)

def epochs_contain(epochs, ts):
    '''
    Returns True if ts falls within one of the epoch boundaries

    Epochs must be sorted.
    '''
    i = np.searchsorted(epochs[:,0], ts)
    j = np.searchsorted(epochs[:,1], ts)
    return i != j

def epochs_overlap(a, b):
    '''
    Returns True where `b` falls within boundaries of epoch in `a`

    Epochs must be sorted.
    '''
    i = np.searchsorted(a[:,0], b[:,0])
    j = np.searchsorted(a[:,1], b[:,1])
    return i != j

def int_to_TTL(a, width):
    '''
    Converts a 1D array of integers to a 2D boolean array based on the binary
    representation of each integer.

    Primarily used in conjunction with TDT's `FromBits` component to reduce the
    overhead of storing and transferring TTL data.  Since a TTL can be
    represented as a single bit (0 or 1), it is wasteful to cast the TTL to an
    int32 before storing the data in a buffer.  `FromBits` combines up to 6 TTL
    channels into a single int32 word.  Since only the first 6 bits are used to
    store the 6 TTL channels, the data can be reduced further.

    1. Using `ShufTo8`, 24 TTL channels can be stored in a single index of a
    serial buffer.
    2. Using `CompTo8`, 4 consecutive samples of data from 6 TTL channels can be
    stored in a single index of a serial buffer.
    3. Combining `ShufTo16` and `CompTo16`, store 2 consecutive samples of data
    from 12 TTL channels in a single index of a serial buffer.

    Using this approach, the memory overhead and amount of data being
    transferred has been reduced by a factor of 24.

    This function uses Numpy's bitshift and bitmask operators, so the algorithm
    should be pretty efficient.

    Parameters
    ==========
    a : array_like
        Sequence of integers to expand into the corresponding boolean array.
        The dtype (either int8, int16 or int32) of the array is used to figure
        out the size of the second dimension.  This will depend on your
        combination of `FromBits` and the shuffle/compression components.

    Returns
    =======
    bitfield : array
        2D boolean array repesenting the bits in little-endian order
    
    Example (note the transpose -- didn't have time to flip around)
    =======
    >>> int_to_TTL([4, 8, 5], width=6).T
    array([[False, False,  True, False, False, False],
           [False, False, False,  True, False, False],
           [ True, False,  True, False, False, False]], dtype=bool)
    '''
    a = np.array(a)
    bitarray = [(a>>bit) & 1 for bit in range(width)]
    return np.array(bitarray, dtype=np.bool)

def bin_array(number, bits):
    '''Return binary representation of an integer as an integer array

    >>> bin_array(8, 4)
    [0, 0, 0, 1]

    >>> bin_array(3, 4)
    [1, 1, 0, 0]
    
    NOTE: This function has not been profiled for speed.
    '''
    return [(number>>bit)&1 for bit in range(bits)]

def test_speed():
    import timeit
    setup = """
from numpy.random import randint
from cns.util.binary_funcs import int_to_TTL
arr = randint(0, 8, 10e3)
    """
    print timeit.timeit("int_to_TTL(arr, 8)", setup, number=20)

if __name__ == "__main__":
    import doctest
    doctest.testmod()
    #test_speed()

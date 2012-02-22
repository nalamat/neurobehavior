#!python

'''
Functions for slicing an array into a series of overlapping chunks
'''
import numpy as np

__author__ = "Brad N. Buran"
__contact__ = "bburan@alum.mit.edu"
__license__ = "GPL"

__all__ = ['chunk_samples', 'chunk_iter', 'slice_overlap']

def chunk_samples(x, max_bytes=10e6, block_size=None, axis=-1):
    '''
    Compute number of samples per channel to load based on the preferred memory
    size of the chunk (as indicated by max_bytes) and the underlying datatype.

    This code is carefully designed to handle boundary issues when processing
    large datasets in chunks (e.g. stabilizing the edges of each chunk when
    filtering and extracting the correct samples from each chunk).

    Parameters
    ----------
    x : ndarray
        The array that will be chunked
    max_bytes : int
        Maximum chunk size in number of bytes.  A good default is 10 MB (i.e.
        10e6 bytes).  The actual chunk size may be smaller than requested.
    axis : int
        Axis over which the data is chunked.
    block_size : None
        Ensure that the number of samples is a multiple of block_size. 

    Examples
    --------
    >>> x = np.arange(10e3, dtype=np.float64)   # 8 bytes per sample
    >>> chunk_samples(x, 800)
    100
    >>> chunk_samples(x, 10e3)                  # 10 kilobyte chunks
    1250
    >>> chunk_samples(x, 10e3, block_size=500)
    1000
    >>> chunk_samples(x, 10e3, block_size=300)
    1200
    >>> x.shape = 5, 2e3
    >>> chunk_samples(x, 800)
    20
    >>> chunk_samples(x, 10e3)
    250

    If the array cannot be broken up into chunks that are no greater than the
    maximum number of bytes specified, an error is raised:

    >>> x = np.ones((10e3, 100), dtype=np.float64)
    >>> chunk_samples(x, 1600)
    Traceback (most recent call last):
        ...
    ValueError: cannot achieve requested chunk size

    The following is OK, however, because we are chunking along the first axis:

    >>> chunk_samples(x, 1600, axis=0)
    2
    '''
    bytes = np.nbytes[x.dtype]

    # Compute the number of elements in the remaining dimensions.  E.g. if we
    # have a 3D array of shape (2, 16, 1000) and wish to chunk along the last
    # axis, then the number of elements in the remaining dimensions is 2x16).
    shape = list(x.shape)
    shape.pop(axis)
    elements = np.prod(shape)
    samples = np.floor(max_bytes/elements/bytes)
    if block_size is not None:
        samples = np.floor(samples/block_size)*block_size
    if not samples:
        raise ValueError, "cannot achieve requested chunk size"
    return int(samples)
    
def chunk_iter(x, chunk_samples, loverlap=0, roverlap=0, padtype='const',
               axis=-1, ndslice=None):
    '''
    Return an iterable that yields the data in chunks.  Only supports chunking
    along the last axis at the moment.

    x : ndarray
        The array that will be chunked
    chunk_samples : int
        Number of samples per chunk along the specified axis
    loverlap : int
        Number of samples on the left to overlap with prior chunk (used to
        handle extraction of features that cross chunk boundaries).  These
        samples are in addition to the number of chunk samples requested.
    roverlap : int
        Number of samples on the right to overlap with the next chunk (used
        to handle extraction of features that cross chunk boundaries).  These
        samples are in addition to the number of chunk samples requested.
    padtype : {'const', }
        Only one padtype is supported for now.  Eventually could support odd and
        even padding as well.
    ndslice : None or slice
        How to slice the other dimensions

    >>> x = np.arange(1000).reshape((4, 250))
    >>> iterable = chunk_iter(x, 5)
    >>> chunk = next(iterable)
    >>> print chunk.shape
    (4, 5)

    >>> print chunk
    [[  0   1   2   3   4]
     [250 251 252 253 254]
     [500 501 502 503 504]
     [750 751 752 753 754]]

    >>> print next(iterable)
    [[  5   6   7   8   9]
     [255 256 257 258 259]
     [505 506 507 508 509]
     [755 756 757 758 759]]

    We can specify some overlap on either side of the chunk.  Total length of
    the chunk will be loverlap+chunk_samples+roverlap:

    >>> iterable = chunk_iter(x, 5, loverlap=1, roverlap=2)
    >>> chunk = next(iterable)
    >>> print chunk.shape
    (4, 8)

    >>> print chunk
    [[  0   0   1   2   3   4   5   6]
     [250 250 251 252 253 254 255 256]
     [500 500 501 502 503 504 505 506]
     [750 750 751 752 753 754 755 756]]

    >>> print next(iterable)
    [[  4   5   6   7   8   9  10  11]
     [254 255 256 257 258 259 260 261]
     [504 505 506 507 508 509 510 511]
     [754 755 756 757 758 759 760 761]]

    Let's take a look at the very last chunk returned.  The right overlapping
    columns are padded with nan values:

    >>> print list(iterable)[-1]
    [[244 245 246 247 248 249 249 249]
     [494 495 496 497 498 499 499 499]
     [744 745 746 747 748 749 749 749]
     [994 995 996 997 998 999 999 999]]

    We can specify the slices along the other dimensions as well.  This is
    particularly useful when working with instances of tables.Array which are
    on-disk.

    >>> ndslice = np.s_[::2, :]
    >>> iterable = chunk_iter(x, 5, loverlap=1, roverlap=2, ndslice=ndslice)
    >>> print next(iterable)
    [[  0   0   1   2   3   4   5   6]
     [500 500 501 502 503 504 505 506]]

    >>> ndslice = np.s_[(1,2), :]
    >>> iterable = chunk_iter(x, 5, loverlap=1, roverlap=2, ndslice=ndslice)
    >>> print next(iterable)
    [[250 250 251 252 253 254 255 256]
     [500 500 501 502 503 504 505 506]]
    '''
    samples = x.shape[axis]
    i = 0
    while i < samples:
        s = slice(i, i+chunk_samples)
        yield slice_overlap(x, s, start_overlap=loverlap, stop_overlap=roverlap,
                            axis=axis, ndslice=ndslice)
        i += chunk_samples

def axis_slice(a, start=None, stop=None, step=None, axis=-1, ndslice=None):
    """
    Take a slice along axis 'axis' from 'a'.

    This code is adapted from scipy.signal._arraytools.  key modification is to
    add a ndslice parameter.

    Parameters
    ----------
    a : numpy.ndarray
        The array to be sliced.
    start, stop, step : int or None
        The slice parameters.
    axis : int
        The axis of `a` to be sliced.
    ndslice : {None or slice object}
        Slices to apply to remaining axes

    Examples
    --------
    >>> a = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
    >>> print axis_slice(a, start=0, stop=1, axis=1)
    [[1]
     [4]
     [7]]

    >>> print axis_slice(a, start=1, axis=0)
    [[4 5 6]
     [7 8 9]]

    >>> ndslice = np.s_[:,::2]
    >>> print axis_slice(a, start=1, axis=0, ndslice=ndslice)
    [[4 6]
     [7 9]]

    Notes
    -----
    The keyword arguments start, stop and step are used by calling
    slice(start, stop, step).  This implies axis_slice() does not
    handle its arguments the exacty the same as indexing.  To select
    a single index k, for example, use
        axis_slice(a, start=k, stop=k+1)
    In this case, the length of the axis 'axis' in the result will
    be 1; the trivial dimension is not removed. (Use numpy.squeeze()
    to remove trivial axes.)
    """
    if ndslice is None:
        ndslice = [slice(None)] * len(a.shape)
    else:
        ndslice = list(ndslice)
    ndslice[axis] = slice(start, stop, step)
    return a[tuple(ndslice)]

def slice_overlap(a, s, start_overlap=0, stop_overlap=0,
                  axis=-1, ndslice=None):

    # First obtain the start, stop and step values of the slice provided.
    samples = a.shape[axis]
    start, stop, step = s.indices(samples)

    # Now, expand the start and stop edges to include the overlapping regions.
    if step is None:
        padded_start = start-start_overlap
        padded_stop = stop+stop_overlap
    else:
        padded_start = start-start_overlap*step
        padded_stop = stop+stop_overlap*step

    # If we are on the first chunk or last chunk, we have some special-case
    # handling to take care of (i.e. padding the extra samples).
    start_padding, stop_padding = 0, 0
    if padded_start < 0:
        start_padding = np.abs(padded_start)
        padded_start = 0
    if padded_stop > samples:
        stop_padding = padded_stop-samples
        padded_stop = samples

    b = axis_slice(a, padded_start, padded_stop, step, axis, ndslice=ndslice)

    if start_padding or stop_padding:
        start_ext = _get_padding(b, start_padding, 'start', 'const', axis)
        stop_ext = _get_padding(b, stop_padding, 'stop', 'const', axis)
        b = np.c_[start_ext, b, stop_ext]
    return b

def _get_padding(x, n, where='start', padtype='const', axis=-1):
    '''
    Return the padding required for the array
    '''
    if where not in ('start', 'stop'):
        raise ValueError, 'Unsupported option for where: ' + str(where)

    if padtype == 'const':
        if where == 'start':
            pad_value = axis_slice(x, start=0, stop=1, axis=axis)
        else:
            pad_value = axis_slice(x, start=-1, axis=axis)
        ones_shape = [1] * len(x.shape)
        ones_shape[axis] = n
        ones = np.ones(ones_shape, dtype=x.dtype)
        return ones * pad_value
    else:
        raise ValueError, 'Unsupported option for padding type'

if __name__ == '__main__':
    import doctest
    doctest.testmod()

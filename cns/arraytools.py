#!python
'''
Functions for array manipulations such as slicing an array into a series of
overlapping chunks.

The core function of this module is `chunk_iter` which provides an extremely
powerful and flexible approach for looping through a large array along a certain
axis while properly handling edge boundaries.  If you deal with continuous
time-series using a fixed sampling rate (e.g.  digital IO data, single and
multi-channel neurophysiology), then you can use this to handle various steps
that are commonly required including:

    * Ensuring the first sample is initialized to a fixed value (e.g. 0 for a
      digital input line).
    * Extracting extra samples on the right and left edges of a given chunk to
      properly stabilize a digital filter algorithm.
    * Discarding the final chunk if it will not be of the desired chunk size.

Other functions are also provided that may be useful.

This module makes heavy use of doctest to ensure the core functions work
properly.  You can run these doctests by typing 'python -m cns.arraytools' at
the command prompt.
'''

from __future__ import division
import numpy as np

__author__ = "Brad N. Buran"
__contact__ = "bburan@alum.mit.edu"
__license__ = "GPL"

__all__ = ['chunk_samples', 'chunk_iter', 'slice_overlap']

import logging
log = logging.getLogger(__name__)

def mask_any(mask, reduction_axes):
    '''
    Reduce a mask along the specified axes using `numpy.any`, then upsize the
    mask to the original shape.

    This is useful for computing "artifact reject" masks.  For example, if you
    have a 3D array containing data from multiple channels, epochs and
    timepoints (with the dimensions in that order), and you wish to reject all
    epochs where the signal exceeded a given value on any timepoint or channel,
    then you could do:

        mask = mask_any(waveforms >= 1e-6, [0, 2])

    Examples
    --------
    >>> x = np.array([[0, 1, 1, 0], [0, 0, 0, 0]], dtype='bool')
    >>> print x
    [[False  True  True False]
     [False False False False]]

    >>> print mask_any(x, [-1])
    [[ True  True  True  True]
     [False False False False]]

    >>> y = np.array([[0, 0, 0, 0], [1, 0, 0, 0]], dtype='bool')
    >>> y = np.dstack([x, y])
    >>> print y
    [[[False False]
      [ True False]
      [ True False]
      [False False]]
    <BLANKLINE>
     [[False  True]
      [False False]
      [False False]
      [False False]]]

    >>> print mask_any(y, [0, -1])
    [[[ True  True]
      [ True  True]
      [ True  True]
      [False False]]
    <BLANKLINE>
     [[ True  True]
      [ True  True]
      [ True  True]
      [False False]]]

    >>> print mask_any(y, [1, 2])
    [[[ True  True]
      [ True  True]
      [ True  True]
      [ True  True]]
    <BLANKLINE>
     [[ True  True]
      [ True  True]
      [ True  True]
      [ True  True]]]

    >>> y[1,0,1] = False
    >>> print y
    [[[False False]
      [ True False]
      [ True False]
      [False False]]
    <BLANKLINE>
     [[False False]
      [False False]
      [False False]
      [False False]]]

    >>> print mask_any(y, [1, 2])
    [[[ True  True]
      [ True  True]
      [ True  True]
      [ True  True]]
    <BLANKLINE>
     [[False False]
      [False False]
      [False False]
      [False False]]]

    '''
    original_shape = mask.shape
    for axis in reduction_axes:
        mask = np.any(mask, axis=axis, keepdims=True)
    for axis in reduction_axes:
        mask = np.repeat(mask, original_shape[axis], axis)
    return mask


def downsampled_mean(x, n, axis=-1):
    '''
    Resizes a N-dimensional array by averaging n elements along the last axis

    Parameters
    ----------
    x : array-like
        Input array
    n : int
        Samples to average
    axis : int, optional
        Axis along which the means are computed.  The default is the last axis.

    >>> a = np.arange(15).reshape((3,5))
    >>> b = downsampled_mean(a, 2)
    >>> print(b)
    [[  0.5   2.5]
     [  5.5   7.5]
     [ 10.5  12.5]]

    >>> a = np.arange(20).reshape((4,5))
    >>> print(a)
    [[ 0  1  2  3  4]
     [ 5  6  7  8  9]
     [10 11 12 13 14]
     [15 16 17 18 19]]

    >>> b = downsampled_mean(a, 2, axis=0)
    >>> print(b)
    [[  2.5   3.5   4.5   5.5   6.5]
     [ 12.5  13.5  14.5  15.5  16.5]]

    '''
    offset = x.shape[axis] % n
    # If offset is zero, don't slice array at all
    if offset:
        x = axis_slice(x, stop=-offset, axis=axis)
    shape = list(x.shape)
    # Convert negative axes
    if axis < 0:
        axis += x.ndim
    shape[axis] = -1
    shape.insert(axis+1, n)
    return x.reshape(shape).mean(axis=axis+1)

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
    
def chunk_iter(x, chunk_samples=None, step_samples=None, loverlap=0, roverlap=0,
               padding='const', axis=-1, ndslice=None, initial_padding=0,
               final_padding=0, discard_uneven=False):
    '''
    Return an iterable that yields the data in chunks along the specified axis.  

    x : ndarray
        The array that will be chunked
    chunk_samples : { None, int }
        Number of samples per chunk along the specified axis.  If None, will
        automatically choose the number of samples based on a fixed memory size
        per chunk (~10 MB).
    step_samples : int or None
        Number of samples between the first sample of each chunk
    loverlap : int
        Number of samples on the left to overlap with prior chunk (used to
        handle extraction of features that cross chunk boundaries).  These
        samples are in addition to the number of chunk samples requested.
    roverlap : int
        Number of samples on the right to overlap with the next chunk (used
        to handle extraction of features that cross chunk boundaries).  These
        samples are in addition to the number of chunk samples requested.
    padding : {'const', number }
        Only constant extension (of the edge value) or a number (e.g. 0 or
        np.nan) are supported for now.  Eventually we could support odd and even
        padding as well.
    ndslice : None or slice
        How to slice the other dimensions
    initial_padding : int
        Number of samples to pad the very first chunk by.  Padding will be
        peformed as requested by `padding`.  This is in addition to
        `left_overlap` (e.g. the total number of samples added will be
        `initial_padding`+`left_overlap`).
    final_padding : int
        Number of samples to pad the final chunk by.  Padding will be peformed
        as requested by `padding`.  This is in addition to `right_overlap` (e.g.
        the total number of samples added will be
        `initial_padding`+`right_overlap`).
    discard_uneven : bool
        If the axis does not have an appropriate number of samples that can be
        segmented evenly, given `chunk_samples` and `chunk_step`, discard the
        final (i.e. "uneven") chunk?  Useful if the processing algorithm
        requires chunks of an expected size.

    TODO - add provision for preloading data in larger chunks and iterating
    through them in smaller ones (e.g. chain the chunk_load).

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
    columns are padded by repeating the final value:

    >>> print list(iterable)[-1]
    [[244 245 246 247 248 249 249 249]
     [494 495 496 497 498 499 499 499]
     [744 745 746 747 748 749 749 749]
     [994 995 996 997 998 999 999 999]]

    We can also specify a different type of padding (e.g. -1).

    >>> iterable = chunk_iter(x, 5, loverlap=1, roverlap=2, padding=-1)
    >>> print list(iterable)[-1]
    [[244 245 246 247 248 249  -1  -1]
     [494 495 496 497 498 499  -1  -1]
     [744 745 746 747 748 749  -1  -1]
     [994 995 996 997 998 999  -1  -1]]

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

    We can also define the step_samples (defined as the number of samples
    between the right edges of the chunks, not including the right overlap).

    >>> iterable = chunk_iter(x, 5, step_samples=10)
    >>> print next(iterable)
    [[  0   1   2   3   4]
     [250 251 252 253 254]
     [500 501 502 503 504]
     [750 751 752 753 754]]

    Note that the next cycle jumps 10 samples ahead

    >>> print next(iterable)
    [[ 10  11  12  13  14]
     [260 261 262 263 264]
     [510 511 512 513 514]
     [760 761 762 763 764]]

    >>> iterable = chunk_iter(x, 5, step_samples=2)
    >>> print next(iterable)
    [[  0   1   2   3   4]
     [250 251 252 253 254]
     [500 501 502 503 504]
     [750 751 752 753 754]]

    Note that the next chunk partially overlaps with the prior chunk

    >>> print next(iterable)
    [[  2   3   4   5   6]
     [252 253 254 255 256]
     [502 503 504 505 506]
     [752 753 754 755 756]]

    Both overlap and step_samples can be combined to produce fancy chunking
    behavior.

    >>> iterable = chunk_iter(x, 10, step_samples=5, roverlap=2, loverlap=2)
    >>> print next(iterable)
    [[  0   0   0   1   2   3   4   5   6   7   8   9  10  11]
     [250 250 250 251 252 253 254 255 256 257 258 259 260 261]
     [500 500 500 501 502 503 504 505 506 507 508 509 510 511]
     [750 750 750 751 752 753 754 755 756 757 758 759 760 761]]

    >>> print next(iterable)
    [[  3   4   5   6   7   8   9  10  11  12  13  14  15  16]
     [253 254 255 256 257 258 259 260 261 262 263 264 265 266]
     [503 504 505 506 507 508 509 510 511 512 513 514 515 516]
     [753 754 755 756 757 758 759 760 761 762 763 764 765 766]]

    >>> print next(iterable)[..., 2:-2]
    [[ 10  11  12  13  14  15  16  17  18  19]
     [260 261 262 263 264 265 266 267 268 269]
     [510 511 512 513 514 515 516 517 518 519]
     [760 761 762 763 764 765 766 767 768 769]]

    Sometimes you wish to pad the final chunk by an array of zeros (e.g. when
    you are processing a digital IO stream, you may wish to ensure that the
    stream has a final value of zero.  This allows you to properly record the
    final falling edge of the trigger even if acquisition stopped before the IO
    reached a low state.

    >>> x = np.ones(1000, dtype='i').reshape((4, 250))
    >>> iterable = chunk_iter(x, 5, final_padding=1, padding=0)
    >>> print list(iterable)[-1]
    [[1 1 1 1 1 0]
     [1 1 1 1 1 0]
     [1 1 1 1 1 0]
     [1 1 1 1 1 0]]

    This is in addition to the `roverlap` argument (so, be careful if you use
    both).

    >>> iterable = chunk_iter(x, 5, roverlap=1, final_padding=1, padding=0)
    >>> print list(iterable)[-1]
    [[1 1 1 1 1 0 0]
     [1 1 1 1 1 0 0]
     [1 1 1 1 1 0 0]
     [1 1 1 1 1 0 0]]

    One can achieve similar chunking using the set the step_samples instead of
    the roverlap and loverlap arguments.  However, the appropriate way to
    achieve the desired chunking behavior may be more intuitive using one
    approach over the other.

    Typically roverlap and loverlap are used when you have algorithms that may
    require data from adjacent chunks to properly process the actual chunk
    itself (e.g. stablizing the edges of a digital filter or performing feature
    detection where the feature may cross the chunk boundary).  

    In contrast, step_samples is used when you have an algorithm that computes a
    running metric (e.g. you can set step_samples to smaller than the chunk_size
    to "smooth out" the running value, or you can set step_samples to greater
    than the chunk size if you only want a "snapshot").

    Now, if you are performing filtering *and* computing a running metric, you
    would likely use all three keywords to achieve the optimal chunking
    behavior.

    All the examples above used values for `chunk_size` and `chunk_step` that
    segmented the array into chunks of equal samples.  However, it's possible to
    specify certain sizes/steps that result in the final chunk having a
    different number of samples.  Depending on how you are using the algorithm,
    this may or may not be the desired behavior.  To illustrate what we mean:

    >>> x = np.arange(55).reshape((5, 11))
    >>> iterable = chunk_iter(x, 4, 3)
    >>> chunks = list(iterable)
    >>> print len(chunks)
    4

    >>> print chunks[0]
    [[ 0  1  2  3]
     [11 12 13 14]
     [22 23 24 25]
     [33 34 35 36]
     [44 45 46 47]]

    >>> print chunks[-1]
    [[ 9 10]
     [20 21]
     [31 32]
     [42 43]
     [53 54]]

    The final chunk only returned 2 samples instead of 4!  This is because the
    array was segmented into 4 chunks since 3 is not enough to cover the full
    span of the array.  To avoid this issue, indicate that the last chunk should
    be discarded if it is uneven:

    >>> iterable = chunk_iter(x, 4, 3, discard_uneven=True)
    >>> chunks = list(iterable)
    >>> print len(chunks)
    3

    >>> print chunks[-1]
    [[ 6  7  8  9]
     [17 18 19 20]
     [28 29 30 31]
     [39 40 41 42]
     [50 51 52 53]]
    '''
    samples = x.shape[axis]
    if step_samples is None:
        step_samples = chunk_samples

    if discard_uneven:
        n_chunks = np.floor((samples-chunk_samples)/step_samples) + 1
    else:
        n_chunks = np.ceil((samples-chunk_samples)/step_samples) + 1
    log.debug('Segmenting array into %d chunks', n_chunks)
    
    lb_indices = np.arange(n_chunks, dtype='i')*step_samples
    ub_indices = lb_indices + chunk_samples

    for lb, ub in zip(lb_indices, ub_indices):
        s = slice(lb, ub)
        yield slice_overlap(x, s, start_overlap=loverlap, stop_overlap=roverlap,
                            axis=axis, ndslice=ndslice, padding=padding,
                            initial_padding=initial_padding,
                            final_padding=final_padding)

def axis_slice(a, start=None, stop=None, step=None, axis=-1, ndslice=None):
    """
    Take a slice along axis 'axis' from 'a'.

    This code is adapted from scipy.signal._arraytools.  Key modification is to
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

def slice_overlap(a, s, start_overlap=0, stop_overlap=0, axis=-1, ndslice=None,
                  padding='const', initial_padding=0, final_padding=0):

    # First obtain the start, stop and step values of the slice provided.
    samples = a.shape[axis]
    start, stop, step = s.indices(samples)

    padded_start = start
    padded_stop = stop

    # Only apply initial/final padding if this chunk is the first or last
    if padded_start == 0 and initial_padding:
        padded_start = start-initial_padding
    if padded_stop == samples and final_padding:
        padded_stop = stop+final_padding

    # Now, expand the start and stop edges to include the overlapping regions
    # (accounting for the step size as needed)
    if step is None:
        padded_start -= start_overlap
        padded_stop += stop_overlap
    else:
        padded_start -= start_overlap*step
        padded_stop += stop_overlap*step

    # If we are on the first chunk or last chunk, we have some special-case
    # handling to take care of (i.e. padding the extra samples).
    n_start_padding, n_stop_padding = 0, 0
    if padded_start < 0:
        n_start_padding = np.abs(padded_start)
        padded_start = 0
    if padded_stop > samples:
        n_stop_padding = padded_stop-samples
        padded_stop = int(samples)

    b = axis_slice(a, padded_start, padded_stop, step, axis, ndslice=ndslice)

    if n_start_padding or n_stop_padding:
        start_ext = _get_padding(b, n_start_padding, 'start', padding, axis)
        stop_ext = _get_padding(b, n_stop_padding, 'stop', padding, axis)
        b = np.c_[start_ext, b, stop_ext]
    return b

def _get_padding(x, n, where='start', padding='const', axis=-1):
    '''
    Return the padding required for the array
    '''
    if padding == 'const':
        if where == 'start':
            pad_value = axis_slice(x, start=0, stop=1, axis=axis)
        elif where == 'stop':
            pad_value = axis_slice(x, start=-1, axis=axis)
        else:
            raise ValueError, 'Unsupported option for where: ' + str(where)
    else:
        pad_value = padding

    shape = list(x.shape)
    shape[axis] = n
    return np.ones(shape, dtype=x.dtype) * pad_value

if __name__ == '__main__':
    #log.setLevel(logging.DEBUG)
    #log.addHandler(logging.StreamHandler())
    import doctest
    doctest.testmod()

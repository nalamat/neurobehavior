import numpy as np

def ts(TTL):
    return np.flatnonzero(TTL)

def edge_rising(TTL):
    return np.r_[0, np.diff(TTL.astype('i'))] == 1

def edge_falling(TTL):
    return np.r_[0, np.diff(TTL.astype('i'))] == -1

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
    #bitarray = map(lambda x: bin_array(x, width), a)
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
    #import doctest
    #doctest.testmod()
    test_speed()

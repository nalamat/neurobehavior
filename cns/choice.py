'''
Each generator takes a sequence and returns a single element on each call.  The
order of the elements returned depends on the algorithm.  The generators do not
modify the sequence (if you must sort the sequence in a certain order, make a
copy of it first).

These are infinite generators (i.e. they never end).
'''

def ascending(sequence):
    '''
    Returns elements from the sequence in ascending order.  When the last
    element is reached, loop around to the beginning.

    >>> choice = ascending([1, 3, 8, 9, 12, 0, 4])
    >>> choice.next()
    0
    >>> choice.next()
    1
    >>> choice.next()
    3
    '''
    from numpy import argsort
    ordered_indices = argsort(sequence)
    while True:
        for i in ordered_indices:
            yield sequence[i]

def descending(sequence):
    '''
    Returns elements from the sequence in descending order.  When the last
    element is reached, loop around to the beginning.

    >>> choice = descending([1, 3, 8, 9, 12, 0, 4])
    >>> choice.next()
    12
    >>> choice.next()
    9
    >>> choice.next()
    8
    '''
    from numpy import argsort
    ordered_indices = argsort(sequence)
    while True:
        for i in reversed(ordered_indices):
            yield sequence[i]

def pseudorandom(sequence, seed=None):
    '''
    Returns a randomly selected element from the sequence.
    '''
    # We need to create a stand-alone generator that cannot be affected by other
    # parts of the code that may require random data (e.g. noise).
    from numpy.random import RandomState
    state = RandomState()
    state.seed(seed)

    n = len(sequence)
    while True:
        i = state.randint(0, n)
        yield sequence[i]

def exact_order(sequence):
    '''
    Returns elements in the exact order they are provided.

    >>> choice = exact_order([1, 3, 8, 9, 12, 0, 4])
    >>> choice.next()
    1
    >>> choice.next()
    3
    >>> choice.next()
    8
    '''
    while True:
        for i in range(len(sequence)):
            yield sequence[i]

def shuffled_set(sequence):
    '''
    Returns a randomly selected element from the sequence and removes it from
    the sequence.  Once the sequence is exhausted, repopulate list with the
    original sequence. 
    '''
    if len(sequence) == 0:
        raise ValueError, "Cannot use an empty sequence"
    from numpy.random import shuffle
    while True:
        indices = range(len(sequence))
        shuffle(indices) # Shuffle is in-place
        for i in indices:
            yield sequence[i]

options = { 'ascending':    ascending,
            'descending':   descending,
            'pseudorandom': pseudorandom,
            'exact order':  exact_order, 
            'shuffled set': shuffled_set,
            }

def get(type, sequence):
    try: len(sequence)
    except TypeError:
        sequence = [sequence]
    return options[type](sequence)

def get_seq(sequence, selector, n=1):
    choice = selector(sequence)
    return [choice.next() for i in range(len(sequence)*n)]

import unittest

class TestChoice(unittest.TestCase):

    def setUp(self):
        self.seq = [1, 3, 8, 9, 12, 0, 4]

    def test_shuffled_set(self):
        seq = get_seq(self.seq, shuffled_set)
        self.assertEqual(set(seq), set(self.seq))

        seq = get_seq(self.seq, shuffled_set, 2)

if __name__ == '__main__':
    import doctest
    doctest.testmod()

    import unittest
    unittest.main()

'''
Each generator takes a sequence and returns a single element on each call.  The
order of the elements returned depends on the algorithm.  The generators do not
modify the sequence (if you must sort the sequence in a certain order, make a
copy of it first).

When adding a generator, use the check_sequence decorator to ensure that
the sequence passed is a shallow copy that you can modify in-place without any
side effects.

These are infinite generators (i.e. they never end).

Random sequences have a hard dependency on Numpy (the built-in Python random
module is suboptimal for scientific work).

Note that each selector uses a shallow copy of the sequence, so you can safely
modify your sequence after you provide it to the selector.

>>> sequence = [1, 3, 8, 9, 12, 0, 4]
>>> choice = exact_order(sequence)
>>> choice.next()
1
>>> sequence[1] = 2
>>> sequence
[1, 2, 8, 9, 12, 0, 4]
>>> choice.next()
3

An error is also raised when an empty sequence is passed.

>>> choice = ascending([])
Traceback (most recent call last):
    ...
ValueError: Cannot use an empty sequence
'''

from functools import wraps

def check_sequence(f):
    '''
    Used to ensure that the sequence has at least one item and passes a shallow
    copy of the sequence to the selector so that we don't have side-effects if
    the sequence gets modified elsewhere in the program.
    '''
    @wraps(f)
    def wrapper(sequence, *args, **kw):
        if len(sequence) == 0:
            raise ValueError, "Cannot use an empty sequence"
        sequence = sequence[:]
        return f(sequence, *args, **kw)
    return wrapper

@check_sequence
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
    sequence.sort()
    while True:
        for i in range(len(sequence)):
            yield sequence[i]

@check_sequence
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
    sequence.sort(reverse=True)
    while True:
        for i in range(len(sequence)):
            yield sequence[i]

@check_sequence
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

@check_sequence
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

@check_sequence
def shuffled_set(sequence):
    '''
    Returns a randomly selected element from the sequence and removes it from
    the sequence.  Once the sequence is exhausted, repopulate list with the
    original sequence. 
    '''
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

import unittest

class TestChoice(unittest.TestCase):

    def get_seq(self, sequence, selector, n=1):
        choice = selector(sequence)
        return [choice.next() for i in range(len(sequence)*n)]

    def setUp(self):
        self.seq = [1, 3, 8, 9, 12, 0, 4]

    def test_shuffled_set(self):
        seq = self.get_seq(self.seq, shuffled_set)
        self.assertEqual(set(seq), set(self.seq))
        seq = self.get_seq(self.seq, shuffled_set, 2)

if __name__ == '__main__':
    import doctest
    doctest.testmod()

    import unittest
    unittest.main()

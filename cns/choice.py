'''
Each generator takes a sequence and returns a single element on each call.  The
order of the elements returned depends on the algorithm.  The generators do not
modify the sequence (if you must sort the sequence in a certain order, make a
copy of it first).
'''

def ascending(sequence):
    '''
    Returns elements from the sequence in ascending order.  When the last
    element is reached, loop around to the beginning.
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
    '''
    from numpy import argsort
    ordered_indices = argsort(sequence)
    while True:
        for i in reversed(ordered_indices):
            yield sequence[i]

def pseudorandom(sequence):
    '''
    Returns a randomly selected element from the sequence.
    '''
    from numpy.random import randint
    while True:
        i = randint(0, len(sequence))
        yield sequence[i]

def exact_order(sequence):
    '''
    Returns elements in the exact order they are provided.
    '''
    while True:
        for i in range(sequence):
            yield sequence[i]

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

def get(type, sequence):
    try: len(sequence)
    except TypeError:
        sequence = [sequence]
    return options[type](sequence)

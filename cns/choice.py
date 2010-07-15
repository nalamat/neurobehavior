import numpy as np

def copy_args(f):
    def _inner(sequence):
        f(sequence[:])
    return _inner

def ascending(sequence):
    index = 0
    sequence.sort()
    while True:
        yield sequence[index]
        index = (index+1)%len(sequence)

def descending(sequence):
    index = 0
    sequence.sort(reverse=True)
    while True:
        yield sequence[index]
        index = (index+1)%len(sequence)

def pseudorandom(sequence):
    while True:
        index = np.random.randint(0, len(sequence))
        yield sequence[index]

def exact_order(sequence):
    index = 0
    while True:
        yield sequence[index]
        index = index+1%len(sequence)

options = { 'ascending':    ascending,
            'descending':   descending,
            'pseudorandom': pseudorandom,
            'exact order':  exact_order, }

def get(type, sequence):
    try: len(sequence)
    except TypeError:
        sequence = [sequence]
    return options[type](sequence)

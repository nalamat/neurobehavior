import time
import numpy as np

################################################################################
# UTILITY FUNCTIONS
################################################################################
def pipeline(func):
    '''Decorator to auto-start a coroutine.'''
    def start(*args, **kwargs):
        cr = func(*args, **kwargs)
        cr.next()
        return cr
    return start

def acquire(generator, samples):
    '''Acquire samples from a generator.

    Paramters
    =========
    generator
        The generator to retrieve the samples from
    samples
        number of samples to acquire
    '''

    return np.fromiter(generator, count=samples, dtype=np.float)

################################################################################
# SOURCES
################################################################################
def rand_source(count, size, sleep):
    """
    A random number generator that produces samples at a fixed time interval.

    This is mainly used for debugging and testing purposes.  Do not use this as
    a source of random numbers!

    Parameters
    ----------
    count : integer
        Number of times the generator can be called
    size : integer
        Number of samples to generate on each call
    sleep : float, seconds
        Minimum time between calls
    """

    # This is mainly used for testing, so we import time to prevent it from
    # getting called when the module is initially loaded.  All import functions
    # take some time to execute, so we want to restrict imports at the
    # module-level to the minimum needed for what we typically expect will be
    # needed during an experiment.
    import time
    for i in range(count):
        yield np.random.randn(size)
        time.sleep(sleep)

################################################################################
# PIPELINES
################################################################################
@pipeline
def lfilter(b, a, target):
    from scipy.signal import lfilter
    margin = len(b)
    n = margin*2

    buffer = (yield)
    while True:
        if buffer.shape[-1] > n:
            filtered_buffer = lfilter(b, a, buffer)
            target.send(filtered_buffer[..., margin:-margin])
            buffer = buffer[..., -margin:]
        data  = (yield)
        print "LFILTER", buffer.shape, data.shape
        buffer = np.c_[buffer, (yield)]

def deinterleave_bits(targets):
    return int_to_TTL(len(targets), deinterleave(targets))

@pipeline
def int_to_TTL(bit_depth, target):
    '''
    Pipeline wrapper around :func:`cns.util.binary_func.int_to_TTL`
    '''
    from cns.util.binary_funcs import int_to_TTL
    while True:
        target.send(int_to_TTL((yield), bit_depth))

@pipeline
def adapter(source, target):
    while True:
        target.send(source.next())

@pipeline
def sp_decimate(n, target):
    '''
    Sends maximum and minimum of every n samples to the target

    Primarily intended for decimating spike waveforms for plotting

    Parameters
    ----------
    n : integer
        Number of samples
    target : coroutine
        Sink that recieves a tuple containing ([max values], [min values]).
    '''

    buffered = (yield)
    while True:
        min_data = []
        max_data = []
        while len(buffered) >= n:
            min_data.append(buffered[:n].min(axis=0))
            max_data.append(buffered[:n].max(axis=0))
            buffered = buffered[n:]
        target.send(max_data, min_data)
        buffered = np.r_[buffered, (yield)]

@pipeline
def moving_average(n, weights, overlap, target):
    '''Pipeline: moving average of n samples using weights.

    Parameters
    ----------
    n : integer
        Number of samples to average
        weights : array_like, float
        Weighting of each sample in the average.  It is assumed that weights are
        normalized.  If None, then all data in the stream are assumed to have a
        weight of 1/n.
    overlap : integer
        Number of samples to overlap for subsequent averages.  This reflects the
        downsampling factor (1=no downsampling).

    If you want to set up different types of averages (e.g. exponential), use
    functools.partial to freeze the weights parameter.
    '''
    #buffered = np.ones(n)*np.nan
    #buffered = np.zeros(n)
    buffered = (yield)
    while True:
        averaged_data = []
        while len(buffered) >= n:
            # This is likely not an optimal way to do this.  If speed starts to
            # become an issue investigate the scipy.weave libraries to see if we
            # can do this more efficiently.
            average = np.average(buffered[:n], weights=weights, axis=0)
            averaged_data.append(average)
            buffered = buffered[n-overlap:]
        target.send(np.array(averaged_data))
        buffered = np.r_[buffered, (yield)]

# Remember that coroutines return a generator object.  Since moving_average
# returns a generator object that has already been "pipelined", we should not
# decorate this function as a pipeline since we are simply returning the
# pipelined generator object.
def simple_moving_average(n, target):
    return moving_average(n, weights=None, overlap=1, target=target)

@pipeline
def buffer(n, target):
    buffer = np.ones(n)*np.nan
    while True:
        buffer = np.r_[buffer, (yield)][-n:]
        target.send(buffer)

@pipeline
def broadcast(targets):
    '''Broadcasts data to multiple targets.

    Parameters
    ----------
    targets
        list of targets to broadcast to
    '''

    while True:
        item = (yield)
        for target in targets:
            target.send(item)

@pipeline
def deinterleave(targets):
    while True:
        item = np.array((yield))
        for i, target in enumerate(targets):
            if target is not None:
                target.send(item[i].ravel())

@pipeline
def divide(divisor, target):
    while True:
        target.send((yield)/divisor)

@pipeline
def add(addend, target):
    while True:
        target.send((yield)+addend)

@pipeline
def threshold(threshold, fill, target):
    while True:
        data = (yield)
        data[data<threshold] = fill
        target.send(data)

@pipeline
def diff(map, target):
    while True:
        data = (yield)
        data[1] -= data[2]
        target.send(data)

################################################################################
# SINKS
################################################################################
@pipeline
def array_data_source_sink(sink):
    while True:
        sink.set_data((yield))

@pipeline
def array_plot_data_sink(sink, name):
    while True:
        sink.set_data(name, (yield))

@pipeline
def file_sink(handle, mode='w'):
    while True:
        data = (yield)
        for sample in data:
            for ch in sample:
                handle.write('%g ' % ch)
            handle.write('\n')

@pipeline
def printer():
    while True:
        print (yield),

import unittest, random, time
from numpy.testing import assert_array_equal

def test_pipeline():
    rand_source(10, 10, 1,
                average(10, None, 2,
                buffer(100,
                printer())))

if __name__ == '__main__':
    test_pipeline()

from __future__ import with_statement

import time
import logging
log = logging.getLogger('pipeline')
logging.basicConfig(level=logging.DEBUG)

import numpy as np

"""The following code uses coroutines, which are a feature not commonly used in
programming languages.  Before attempting to understand the code here, several
resources are suggested:

    1) A curious course on concurrency and coroutines:
       http://www.dabeaz.com/coroutines/
    2) PEP 342: http://www.python.org/dev/peps/pep-0342/
"""

################################################################################
# UTILITY FUNCTIONS
################################################################################
def pipeline(func):
    def start(*args, **kwargs):
        cr = func(*args, **kwargs)
        cr.next()
        return cr
    return start

def acquire(generator, samples):
    return np.fromiter(generator, count=samples, dtype=np.float)

################################################################################
# SOURCES
################################################################################
# Note sources are not coroutines but rather generators that produce data.
def rand_source(count, size, sleep):
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
def adapter(source, target):
    while True:
        target.send(source.next())
    
@pipeline
def sp_decimate(n, target):
    buffered = (yield)
    while True:
        min_data = []
        max_data = []
        while len(buffered) >= n:
            min_data.append(buffered[:n].min(axis=0))
            max_data.append(buffered[:n].max(axis=0))
            buffered = buffered[n:]
        target.send(max_data)
        print 'sent data'
        buffered = np.r_[buffered, (yield)]
            
@pipeline
def moving_average(n, weights, overlap, target):
    '''Moving average of n samples using weights and sends to the target.  If
    weights is None, then all data in the stream are assumed to have a weight of
    1.  Offset is the downsampling factor (1=no downsampling).  Use weights to
    create different types of moving averages (e.g. exponential averaging).
    '''
    # NOTE TO SELF: Look into functools.partial to see if we can use this module
    # to set up different types of averages using pre-defined weights.
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
    while True:
        item = (yield)
        for target in targets:
            target.send(item)

@pipeline
def deinterleave(targets):
    n = len(targets)
    while True:
        item = np.array((yield))
        for i, target in enumerate(targets):
            if target is not None:
                target.send(item[:,i::n].ravel())

@pipeline
def deinterleave_2d(targets):
    n = len(targets)
    while True:
        item = np.array((yield))
        for i, target in enumerate(targets):
            if target is not None:
                target.send(item[i])

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

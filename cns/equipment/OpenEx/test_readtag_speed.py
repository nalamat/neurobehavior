from cns import equipment
from timeit import timeit
import numpy as np
import time

from cns import equipment
circuit = equipment.dsp().load('test/data_reduction_RX6', 'RX6')
    
def test_new_idea():
    #data = np.arange(12, dtype=np.int8)
    data = np.arange(12, dtype=np.int8)
    circuit.buf.WriteTagV(0, data.view(np.float32))
    #circuit.buf.WriteTagVEX('buf', 0, "F32", data.view(dtype=np.float64))
    #circuit.buf.WriteTagVEX('buf', 0, "F32", data)
    data = np.array(circuit.buf.ReadTagV(0, 3), dtype=np.float32)
    print data.view(np.int8)
    #print data.view(dtype=np.int8)

def readtagv(n):
    return circuit.dsp.ReadTagV('buf', 0, n)

def readtagvex(n, s='F32', d='F32', ch=1):
    return circuit.dsp.ReadTagVEX('buf', 0, n, s, d, ch)[0]

def readtagvex_mc8(n, s='I8', d='I8', ch=1):
    return circuit.dsp.ReadTagVEX('mc8', 0, n, s, d, ch)[0]

def readtagv_mc8(n):
    data = circuit.dsp.ReadTagV('buf', 0, n/4)
    return np.array(data, dtype=np.float32).view(np.int8)

def convert(n):
    return test_data.view(np.int8)

def mc_read():
    return circuit.mc.read()

def mc16_read():
    return circuit.mc16.read()

def mc8_read():
    return circuit.mc8.read()

raw_funcs = [readtagv, readtagvex, readtagvex_mc8, readtagv_mc8]

def check_returned_data():
    for f in raw_funcs:
        print '%s returned %d samples' % (f.__name__, len(f(25e3)))

def run_tests(s, n):
    f_names = [f.__name__ for f in raw_funcs]
    setup = 'from __main__ import ' + ' ,'.join(f_names)
    circuit.start()
    circuit.trigger(1)
    #print '%d SAMPLES, %d REPETITIONS' % (s, n)
    print '\n\n%15s\t\tTime for %d samples (ms)' % ('Function', s)
    print '-----------------------------------------------------'
    for f in f_names:
        result = timeit('%s(%d)' % (f, s), setup, number=n)
        print '%15s\t\t%.8f' % (f, result*1e3)
        
def run_comp_tests(s, n):
    setup = 'from __main__ import mc_read, mc16_read, mc8_read'
    circuit.mc8.initialize(channels=4, src_type=np.int8, sf=31, compression='decimated')
    circuit.mc16.initialize(channels=4, src_type=np.int16, sf=6553, compression='decimated')
    circuit.mc.initialize(channels=4)
    circuit.nHi.value = s
    circuit.start()
    circuit.trigger(1)
    time.sleep(2)
    
    #print '%d SAMPLES, %d REPETITIONS' % (s, n)
    for f in ['mc_read', 'mc16_read', 'mc8_read']:
    #for f in ['mc_read']:
        result = timeit('%s()' % f, setup, number=1)
        print '%15s %.8f' % (f, result)
        
def suite():
    n = 25
    run_tests(500, n)
    run_tests(5e3, n)
    run_tests(25e3, n)
    run_tests(100e3, n)
                             
if __name__ == '__main__':
    #readtag(10)
    check_returned_data()
    suite()
    #run_comp_tests(4, 1)

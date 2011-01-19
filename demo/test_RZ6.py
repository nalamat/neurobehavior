import sys
from os.path import abspath, dirname, join
libdir = abspath(join(dirname(__file__), '..'))
sys.path.insert(0, libdir)

import logging
logging.basicConfig(level=logging.DEBUG)

from cns.equipment.TDT import Circuit

circuit = Circuit('test_RZ6', 'RZ6')
circuit.start()
fs = circuit.fs

from numpy import *
t = arange(fs)/fs
tone_waveform = sin(2*pi*1e3*t)
noise_waveform = random.random(len(t))

tone = circuit.get_buffer('DAC-A1')
tone.set(tone_waveform)

noise = circuit.get_buffer('DAC-A2')
noise.set(noise_waveform)

import time
print "sleeping"
time.sleep(2)
print "awake"
circuit.trigger('A', 'high')

time.sleep(2)
print "switch"
circuit.trigger(1)
time.sleep(2)

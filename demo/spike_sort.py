import numpy as np
from tdt import DSPCircuit

coeffs = np.zeros((32, 3))
coeffs[15] = [0.0004, 0.0001, 1]
coeffs[12] = [0.0001, 0.0001, 2]
#coeffs[:3] = [-0.3, 0.2, 1]

import tables
from cns.channel import FileSnippetChannel

from cns.data.h5_utils import get_temp_file
from cns.channel import FileSnippetChannel

datafile = get_temp_file()

spike_channel = FileSnippetChannel(snippet_size=30, node=datafile.root,
        name='Spikes')

# Load the physiology circuit
circuit = DSPCircuit('e:/programs/neurobehavior/stable/components/physiology.rcx', 'RZ5')
print coeffs
circuit.set_coefficients('spike1_c', coeffs.ravel())
circuit.set_tag('spike1_a', 0.0001)

# Get the spikes buffer
spikes = circuit.get_buffer('spike1', 'r', block_size=32)

# Start the circuit (it requires a zBUS trig A to enable recording)
circuit.start()
circuit.trigger('A', 'high')

# Collect some data
import time
time.sleep(3)

data = spikes.read().ravel()

from pylab import *

data.shape = -1, 32
sort_codes = data[:, -1].view('int32')
codes = np.unique(sort_codes)
print sort_codes

spike_channel.send(data[:,1:-1], data[:,0].view('int32'),
        data[:,-1].view('int32'))
for i, (code, color) in enumerate(zip(sort_codes, ('b', 'g', 'r'))):
    subplot(1, 3, i+1)
    data = spike_channel.get_recent(5, code)
    plot(data.T, c=color)
    data = spike_channel.get_recent_average(5, code)
    plot(data, c=color, lw=3)
show()

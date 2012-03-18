import numpy as np
import tables
from cns.channel import ProcessedFileMultiChannel 

raw = tables.openFile('c:/users/brad/desktop/110911_tail_behavior.hd5', 'r')
ext = tables.openFile('c:/users/brad/desktop/110911_tail_behavior_extracted.hd5', 'r')
raw = raw.root.PositiveDTCLExperiment_2011_09_11_21_33_30.data.physiology.raw
node = ProcessedFileMultiChannel.from_node(raw, 
                                           filter_pass='bandpass',
                                           freq_hp=300,
                                           freq_lp=6000,
                                           filter_order=8,
                                           bad_channels=ext.root.bad_channels[:]-1)

extracted_channels = ext.root.extracted_channels[:]-1
n = 10
channel = 7
mask = ext.root.channels == 7

offset = -10e3
size = 100
indices = ext.root.timestamps[mask]
print len(indices)
import sys
sys.exit()
waveforms = ext.root.waveforms[mask]

b, a = node.filter_coefficients
ext_b = ext.root.filter_b.read()
ext_a = ext.root.filter_a.read()

print np.equal(b, ext_b)
print np.equal(a, ext_a)

extracted = []
for i in indices:
    r = node[extracted_channels, i-7:i+19]
    extracted.append(r)

from pylab import *
#figure()
plot(waveforms[:,2,:].T, 'k')

extracted = np.c_[extracted]
#figure()
plot(extracted[:,2,:].T, 'r')
show()

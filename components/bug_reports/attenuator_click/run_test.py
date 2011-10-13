import numpy as np
from pylab import *
from numpy import fft
from tdt import DSPCircuit
import time

circuit = DSPCircuit('create_att_click', 'RZ6')
data_buffer = circuit.get_buffer('in', 'r')
circuit.start()
circuit.set_tag('start_att', 60)
circuit.set_tag('DC', 0)

time.sleep(0.2)

for end in [0, 20, 40, 60, 80]:
    circuit.set_tag('end_att', end)
    data = data_buffer.acquire(1, 'acquiring', False, 1)
    data = data.mean(0)
    subplot(211)
    plot(data)
    sp = fft.fft(data)
    freq = fft.fftfreq(data.size, 1/200e3)
    n = int(len(freq)/2.)
    freq = freq[:n]
    sp = sp[:n]
    subplot(212)
    plot(freq, 20*np.log10(np.absolute(sp)), label=str(end))
    time.sleep(0.2)

legend()
subplot(211)
axis(xmax=1000)
axvline(500)
xlabel('Time (samples)')
ylabel('Amplitude (V)')
subplot(212)
axis(xmax=50e3)
xlabel('Frequency')
ylabel('Magnitude (dB)')
show()

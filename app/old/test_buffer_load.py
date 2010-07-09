from cns.signal.type import Tone
from cns import equipment

circuit = equipment.backend.load('aversive-behavior', 'RX6')
signal = Tone(frequency=5)
signal.fs = circuit.fs

buffer = circuit.open('int_buf', 'w', len(signal))
circuit.set_buffer('int_buf', signal)
circuit.start()

i = 0
while True:
    if buffer.block_processed:
        samples = signal.read_block()
        buffer.write(samples)
        i += 1
        print i
    if i >= 3: break

from pylab import plot, show

data = circuit.get_buffer('int_buf', len(signal))
plot(data, 'r')
plot(signal.signal, 'k')
show()

from tdt import DSPCircuit
#circuit = DSPCircuit('ZeroTag_example', 'RZ6')
#buffer = circuit.get_buffer('buffer', 'w')
circuit = DSPCircuit('positive-behavior', 'RZ6')
buffer = circuit.get_buffer('speaker', 'w')
circuit.start()
circuit.trigger('A', 'high')
import time
print circuit
time.sleep(1)
buffer.clear()

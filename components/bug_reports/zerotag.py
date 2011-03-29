from tdt import DSPCircuit
circuit = DSPCircuit('ZeroTag_example', 'RZ6')
buffer = circuit.get_buffer('buffer', 'w')
buffer.clear()

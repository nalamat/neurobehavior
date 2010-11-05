import audiere
DEVICE = audiere.open_device()
import numpy as np

def load(circuit, device):
    # Hack alert!!!!
    return OutputCircuit()

class ComputerBuffer(object):

    def __init__(self):
        self.buffer = np.array([])

    def set(self, data):
        self.buffer = np.array(data)

class ComputerTag(object):

    def __init__(self, value=0):
        self.value = 0

    def set(self, value):
        self.value = value

    def get(self, value):
        return self.value

class OutputCircuit(object):

    fs = 100e3

    def __init__(self, device=DEVICE):
        self.device = device
        self.DAC1a = ComputerBuffer()
        self.DAC1b = ComputerBuffer()

        self.TTL1a = ComputerBuffer()
        self.TTL1b = ComputerBuffer()
        self.TTL2a = ComputerBuffer()
        self.TTL2b = ComputerBuffer()
        self.TTL3a = ComputerBuffer()
        self.TTL3b = ComputerBuffer()

        self.buffer = ComputerTag(0)
        self.reset = ComputerTag()
        self.switch = ComputerTag()
        self.set_current(self.buffer.value)

    def set_current(self, buffer):
        current = self.DAC1a if buffer==0 else self.DAC1b
        self.stream = self.device.open_array(current.buffer, self.fs)
        self.buffer.value = buffer

    def trigger(self, trigger):
        if trigger == 1:
            self.stream.play()
        elif trigger == 2:
            self.stream.stop()
        elif trigger == 3:
            self.stream.stop()
            self.set_current(int(not self.buffer.value))
            self.stream.play()

    def start(self):
        # Dummy function to be compatible with DSPCircuit
        pass

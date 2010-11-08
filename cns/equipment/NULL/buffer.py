import numpy as np
from cns.pipeline import pipeline
from cns.buffer import BlockBuffer

import logging
log = logging.getLogger(__name__)

def source(*arg, **kw):
    if 'channels' in kw: channels = kw['channels']
    else: channels = 1
    if 'multiple' in kw: multiple = kw['multiple']
    else: multiple = 1
    while True:
        samples = np.random.randint(1000)
        samples = int(samples/multiple)*multiple
        yield np.random.rand(samples, channels)

@pipeline
def sink(source, name, length=None):
    while True: (yield)

class DSPBuffer(BlockBuffer):

    def __init__(self, *arg, **kw):
        self.blocks = 2
        pass

    def samples_processed(self):
        return np.random.randint(1000)
    
    def write(self, data):
        try: super(DSPBuffer, self).write(data.signal)
        except: super(DSPBuffer, self).write(data)

    def get_block_processed(self):
        return self.samples_processed()>=self.block_size

    block_processed = property(get_block_processed)

    def _read(self, offset, length):
        raise NotImplementedError

    def _write(self, offset, data):
        pass
    
    def __len__(self):
        return 100e3
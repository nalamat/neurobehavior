import logging
log = logging.getLogger(__name__)
import numpy as np

from . import buffer

def connect(*arg, **kw):
    log.debug('connect(%r, %r)' % (arg, kw))

def load(circuit, device):
    log.debug('load(%r, %r)' % (circuit, device))
    return Circuit()

def init_device(circuit, device, **kw):
    log.debug('init_device(%r, %r, %r)' % (circuit, device, kw))
    return Circuit()

def set_attenuation(atten, device):
    log.debug('set_attenuation(%r, %r)' % (atten, device))
    
    
class Circuit(object):

    epsilon = 1e-6
    fs = 50e3

    def start(self, **kw):
        log.debug('start(%r)' % kw)

    def set(self, **kw):
        log.debug('set(%r)' % kw)

    def reload(self):
        log.debug('reload')

    def stop(self):
        log.debug('stop')

    def __setattr__(self, name, value):
        log.debug('setattr(%r, %r)' % (name, value))

    def __getattr__(self, name):
        # Check to see if it is a tag
        try: return self.open_buffers[name]
        except KeyError: pass       # the buffer has not been opened
        return np.random.randint(1000)

    def __str__(self):
        return self.__class__.__name__

    def get_status(self):
        return True

    def _get_running(self):
        return False

    running = property(_get_running)

    def _get_maxfreq(self):
        return self.fs/2.
    
    open_buffers = {}
    
    # Returns Nyquist
    MAX_FREQUENCY = property(_get_maxfreq)

    def open(self, name, mode='r', length=None, **kw):
        if mode == 'r': pipe = buffer.source(**kw)
        elif mode == 'w': pipe = buffer.DSPBuffer(**kw)
        self.open_buffers[name] = pipe
        return pipe

    def check_buffer(self, buffer, length=0):
        pass

    def get_buffer(self, buffer, samples):
        '''Assumes data is written starting at the first index of the buffer.'''
        self.check_buffer(buffer, samples)
        return np.array(self.dsp.ReadTagV(buffer, 0, samples))

    def set_buffer(self, buffer, data, zero=True):
        pass

    def zero_buffer(self, buffer):
        pass

    def buffer_duration(self, buffer):
        return np.random.randint(1000)

    def trigger(self, trig):
        pass

    def acquire(self, buffer, samples, trigger=None, timeout=1):
        pass

    def sec_to_samples(self, sec):
        return int(sec*self.fs)

    def samples_to_sec(self, samples):
        return samples/self.fs

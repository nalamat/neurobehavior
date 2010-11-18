import numpy as np

def cos2ramp(n):
    return np.sin(np.linspace(0, np.pi / 2., n)) ** 2

def cosramp(n):
    return np.sin(np.linspace(0, np.pi / 2., n))

def linramp(n):
    return np.arange(n, dtype='f') / n

def generate_envelope(n, ramp_type, ramp_n):
    '''
    Generate envelope
    '''
    if ramp_type != 'cosine squared':
        raise ValueError, "not supported"
    #ramp = generate_ramp(ramp_type, ramp_n)
    ramp = cos2ramp(ramp_n)
    return np.r_[ramp, np.ones(n-2*ramp_n), ramp[::-1]]

def cos2taper(waveform, ramp_n):
    return waveform * generate_envelope(len(waveform), 'cosine squared', ramp_n)

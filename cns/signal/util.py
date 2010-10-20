import numpy as np

def generate_ramp(ramp_type, n):
    '''
    Generate array of n samples describing ramp shape on a scale of 0 to 1
    '''
    if ramp_type == 'cosine squared':
        return np.sin(np.linspace(0, np.pi / 2., n)) ** 2
    elif ramp_type == 'cosine':
        return np.sin(np.linspace(0, np.pi / 2., n))
    elif ramp_type == 'linear':
        return np.arange(n, dtype='f') / n

def generate_envelope(n, ramp_type, ramp_n):
    '''
    Generate envelope
    '''
    ramp = generate_ramp(ramp_type, ramp_n)
    return np.r_[ramp, np.ones(n-2*ramp_n), ramp[::-1]]

def taper(waveform, ramp_type, ramp_n):
    return waveform * generate_envelope(len(waveform), ramp_type, ramp_n)

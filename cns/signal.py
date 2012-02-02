import numpy as np

def time(fs, duration, t0=0):
    '''
    Return a time vector that can be used in computing and plotting signal
    waveforms

    Parameters
    ----------
    fs : float
        Sampling frequency
    duration : float
        Duration of vector
    t0 : float
        Time of first sample
    '''

    samples = int(duration*fs) 
    return (np.arange(samples)+t0)/fs

def cos2ramp(n):
    return np.sin(np.linspace(0, np.pi / 2., n)) ** 2

def generate_envelope(n, ramp_n):
    r'''
    Generate normalized envelope

    Parameters
    ----------
    n : int
        Total duration of envelope in samples (from start of rising edge to end
        of falling edge)
    ramp_n : int
        Duration of ramp in samples

    Returns
    -------
    array of length n containing normalized values for the ramp [0 to 1]

    Raises
    ------
    ValueError if the ramp cannot fit inside the requested envelope duration
    
    '''
    if 2*ramp_n > n:
        mesg = "Ramp duration must be less than half the envelope duration"
        raise ValueError, mesg
    ramp = cos2ramp(ramp_n)
    return np.r_[ramp, np.ones(n-2*ramp_n), ramp[::-1]]

def am_eq_power(depth):
    '''
    Given the modulation depth for a token, return the scaling factor to
    multiply the waveform by so that the power in the modulated token is equal
    to the power in the unmodulated token.
    '''
    return (3.0/8.0*depth**2-depth+1)**0.5

def am_eq_phase(depth, direction='positive'):
    '''
    Given the modulation depth, return the starting phase of the modulation that
    ensures a smooth transition from an unmodulated token to the modulated
    token.

    depth : [0, 1]
        Modulation depth as a fraction
    direction : {'positive', 'negative'}
        Direction you would like the modulation to move in (i.e. downwards or
        upwards).
    '''
    if depth == 0:
        # This is the easy case
        return 0
    eq_power = am_eq_power(depth)
    z = 2.0/depth*eq_power-2.0/depth+1
    phi = np.arccos(z)
    return 2*pi-phi if direction == 'positive' else phi

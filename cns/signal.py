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

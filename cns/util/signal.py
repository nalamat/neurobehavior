'''
Created on Jun 16, 2010

@author: admin_behavior
'''
import numpy as np

def rfft(fs, signal):
    N = len(signal)
    freq = fs / 2 * np.linspace(0, 1, N / 2 + 1)
    component = np.fft.rfft(signal, N) / N
    power = np.abs(component)
    phase = np.angle(component)
    return freq, power, phase

def dbtopa(db):
    return 10 ** (db / 20.) * 2e-5

def patodb(pa):
    return 20 * np.log10(pa / 2e-5)

def rfft_freqs(N, fs):
    return fs / 2. * np.linspace(0, 1, N)

def get_rms_power_window(fs, signal, freq, window=5):
    f, power, phase = rfft(fs, signal)
    lb, ub = freq - window, freq + window
    window = (f >= lb) & (f < ub)
    i = power[window].argmax()
    return (power[window].sum()**2) ** 0.5, phase[window][i]
    #return power[window].max(), -1

def get_rms_power_cr(fs, signal, freq, cr=27.5):
    '''Uses the estimated critical ratio of 25 for gerbils as described in
    Kittel et al., 2002. Hearing Research 164:1-2 pp.69-76.  We assume the CR is
    uniform across frequencies (it ranges from 25 to 30).
    '''
    return get_rms_power_window(fs, signal, freq, freq / cr)

def get_rms_power_conv(fs, signal, freq):
    # TODO: this does not appear to give us the right number for the pistonphone cal!
    t = np.arange(len(signal)) / fs

    real_component = np.sin(2*np.pi*t*freq) * signal
    imag_component = np.cos(2*np.pi*t*freq) * signal

    real = real_component.mean()
    imag = imag_component.mean()
    vector = complex(real, imag)

    return abs(vector), angle(vector)

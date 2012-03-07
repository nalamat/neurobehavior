import numpy as np
from scipy import signal

def rfftfreq(n, d=1.0):
    """
    Return the single-sided Discrete Fourier Transform sample frequencies.

    The returned float array contains the positive-frequency bins in
    cycles/unit (with zero at the start) given a window length `n` and a
    sample spacing `d`::

      f = [0, 1, ..., n/2-1] / (d*n)         if n is even
      f = [0, 1, ..., (n-1)/2] / (d*n)       if n is odd

    Parameters
    ----------
    n : int
        Window length.
    d : scalar
        Sample spacing.

    Returns
    -------
    out : ndarray
        The array of length `n`, containing the sample frequencies.

    Examples
    --------
    >>> signal = np.array([-2, 8, 6, 4, 1, 0, 3, 5], dtype=float)
    >>> fourier = np.fft.rfft(signal)
    >>> n = signal.size
    >>> timestep = 0.1
    >>> freq = rfftfreq(n, d=timestep)
    >>> freq
    array([ 0.  ,  1.25,  2.5 ,  3.75])
    """
    n = n//2+1
    return np.arange(0, n, dtype='f')/(n*d)

def rad2complex(radians):
    '''
    Converts angle, in radians, to complex notation

    >>> print rad2complex(0)
    (1+0j)

    >>> print np.sqrt(2)*rad2complex(np.pi/4)
    (1+1j)

    >>> np.angle(rad2complex(np.pi/2)) == np.pi/2
    True
    '''
    return np.exp(1j*radians)

def mirrorfft(rfft):
    '''
    Constructs the complex, 2-sided FFT spectrum given the complex, single-sided
    FFT spectrum.  
    
    The return value of this function is typically used in conjunction with ifft
    to compute the inverse discrete Fourier transform.  Be sure to check
    numpy.fft.irfft before using mirrorfft as that may be better suited to your
    purpose.

    rfft : array-like
        Complex form of the single-sided spectrum (i.e. the real frequencies).
        This assumes the input is purely real (i.e. the negative frequency terms
        are just the complex conjugate of the corresponding positive-frequency
        terms and therefore redundant when computing the spectrum).

    The single-sided spectrum includes the DC component.
    '''
    n_rfft = len(rfft)
    n = 2*n_rfft if (n_rfft % 2) else 2*n_rfft-1
    fft = np.zeros(n, dtype='complex')

    # First portion is the positive-frequency component of the spectrum
    # (starting with the DC component)
    fft[:n_rfft] = rfft

    # Second portion is the negative-frequency component and is the complex
    # conjugate of the positive-frequency compomnent and in reverse order.  Note
    # that this portion excludes the DC component.
    if n_rfft % 2:
        # If we have an even number of positive-frequency components (including
        # zero), then this means the two-sided spectrum has an extra
        # negative-frequency component at fft[n_rfft].  Since there is no
        # matching positive-frequency component, we skip this slot.
        fft[n_rfft+1:] = np.conj(rfft[1:])[::-1]
    else:
        # If we have an odd number of positive-frequency components, then the
        # positive and negative frequencies will be perfectly symmetrical around
        # the DC offset
        fft[n_rfft:] = np.conj(rfft[1:])[::-1]

    return fft

def ispow2(n):
    '''
    True if n is a power of 2, False otherwise

    >>> ispow2(5)
    False
    >>> ispow2(4)
    True
    '''
    return (n & (n-1)) == 0

def nextpow2(n):
    '''
    Given n, return the nearest power of two that is >= n

    >>> nextpow2(1)
    1
    >>> nextpow2(2)
    2
    >>> nextpow2(5)
    8
    >>> nextpow2(17)
    32

    Floating point values can also be used

    >>> nextpow2(18.1)
    32
    >>> nextpow2(32.5)
    64
    '''
    n = int(np.ceil(n))

    if ispow2(n):
        return n
    
    count = 0
    while n != 0:
        n = n >> 1
        count += 1
    return 1 << count

def dbtopa(db):
    '''
    Convert dB SPL to Pascal

    .. math:: 10^(dB/20.0)/20e-6
    
    >>> print dbtopa(100)
    2.0
    >>> print dbtopa(120)
    20.0
    >>> print patodb(dbtopa(94.0))
    94.0

    Will also take sequences:
    >>> print dbtopa([80, 100, 120])
    [  0.2   2.   20. ]
    '''
    db = np.asarray(db)
    return 10**(db/20.0)*20e-6

def patodb(pa):
    '''
    Convert Pascal to dB SPL

    .. math:: 20*log10(pa/20e-6)

    >>> print round(patodb(1))
    94.0
    >>> print patodb(2)
    100.0
    >>> print patodb(0.2)
    80.0

    Will also take sequences:
    >>> print patodb([0.2, 2.0, 20.0])
    [  80.  100.  120.]
    '''
    pa = np.asarray(pa)
    return 20.0*np.log10(pa/20e-6)

def rms(waveform):
    '''
    Compute root mean square power of waveform
    '''
    return (waveform**2).mean()**0.5
    
def normalize_rms(waveform, out=None):
    '''
    Normalize RMS power to 1 (typically used when generating a noise waveform
    that will be scaled by a calibration factor)

    waveform : array_like
        Input array.
    out : array_like
        An array to store the output.  Must be the same shape as `waveform`.
    '''
    return np.divide(waveform, rms(waveform), out)

def filter_response(b, a, fs, axes_magnitude=None, axes_phase=None):
    # We need to keep the import inside here because a lot of GUI applications
    # based on PyQt may want to use Neurogen, and Matplotlib currently does not
    # play well with these applications
    from pylab import figure
    w, h = signal.freqz(b, a)
    f = w*0.5*fs/np.pi

    if axes_magnitude is None and axes_phase is None:
        fig = figure()
        axes_magnitude = fig.add_subplot(211)
        axes_phase = fig.add_subplot(212)

    if axes_magnitude is not None:
        axes_magnitude.semilogx(f, 20*np.log10(np.abs(h)))
    if axes_phase is not None:
        axes_phase.semilogx(f, np.unwrap(np.angle(h)))

def rfft(signal, fs):
    '''
    Compute the real spectrum of the signal
    '''
    N = len(signal)
    freq = rfftfreq(N, 2.0/fs)
    component = np.fft.rfft(signal, N) / N
    power = np.abs(component)
    phase = np.unwrap(np.angle(component))
    return freq, power, phase

def signal_spectrum(signal, fs, reference=1, axes_magnitude=None,
        axes_phase=None, plot_kw=None):
    # We need to keep the import inside here because a lot of GUI applications
    # based on PyQt may want to use Neurogen, and Matplotlib currently does nto
    # play well with hese applications
    from pylab import gcf
    freq, force, phase = rfft(signal, fs)

    if plot_kw is None:
        plot_kw = {}

    if axes_magnitude is None and axes_phase is None:
        fig = gcf()
        axes_magnitude = fig.add_subplot(211)
        axes_phase = fig.add_subplot(212, sharex=axes_magnitude)

    if axes_magnitude is not None:
        axes_magnitude.semilogx(freq, 20*np.log10(force/reference), **plot_kw)
    if axes_phase is not None:
        axes_phase.semilogx(freq, phase, **plot_kw)

if __name__ == '__main__':
    import doctest
    doctest.testmod()

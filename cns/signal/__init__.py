from .signal import Signal
#from .signal_selector_dialog import SignalDialog

from scipy import signal
from numpy import log10
#from pylab import *

#Plot frequency and phase response
#def mfreqz(b,a=1, fs=1):
#    w,h = signal.freqz(b,a)
#    h_dB = 20 * log10 (abs(h))
#    subplot(211)
#    #plot(w/max(w),h_dB)
#    semilogx(w/pi/2*fs,h_dB)
#    ylim(-150, 5)
#    ylabel('Magnitude (db)')
#    xlabel(r'Normalized Frequency (x$\pi$rad/sample)')
#    title(r'Frequency response')
#    subplot(212)
#    h_Phase = unwrap(arctan2(imag(h),real(h)))
#    plot(w/max(w),h_Phase)
#    ylabel('Phase (radians)')
#    xlabel(r'Normalized Frequency (x$\pi$rad/sample)')
#    title(r'Phase response')
#    subplots_adjust(hspace=0.5)
#
##Plot step and impulse response
#def impz(b,a=1):
#    l = len(b)
#    impulse = repeat(0.,l); impulse[0] =1.
#    x = arange(0,l)
#    response = signal.lfilter(b,a,impulse)
#    subplot(211)
#    stem(x, response)
#    ylabel('Amplitude')
#    xlabel(r'n (samples)')
#    title(r'Impulse response')
#    subplot(212)
#    step = cumsum(response)
#    stem(x, step)
#    ylabel('Amplitude')
#    xlabel(r'n (samples)')
#    title(r'Step response')
#    subplots_adjust(hspace=0.5)

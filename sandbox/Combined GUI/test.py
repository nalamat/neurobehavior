import scipy
import scipy.signal
import numpy

t = numpy.random.rand(22050)
freq = 20
sinusoidal = t#numpy.sin(2*numpy.pi*freq*t/float(len(t)))

b, a =scipy.signal.iirdesign(wp=[0.4,0.6], ws=[0.2,0.8], gpass=3, gstop=48, ftype='butter', output='ba')
sinusoidal = scipy.signal.lfilter(b, a, sinusoidal)
ft = numpy.fft.fft(sinusoidal)
print "Fourier Transform:",ft

frequencies = numpy.fft.fftfreq(t.shape[-1], 1/22050.)
print "Frequencies:",frequencies

print "Max Frequency:",max(frequencies)

maxItem = None
maxIndex = None

for i in xrange(len(ft)):
	value = ft[i]
	if maxItem < abs(value) or maxItem == None:
		maxItem = abs(value)
		maxIndex = i

print maxItem, maxIndex, frequencies[maxIndex]
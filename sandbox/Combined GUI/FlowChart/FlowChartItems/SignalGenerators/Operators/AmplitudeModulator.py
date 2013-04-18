import wx
import numpy
import math
import scipy
import scipy.signal
import FlowChartItems.SignalGenerators.Operators as Operators
from SignalParameter import SignalParameter, WaveInput

class AmplitudeModulator(Operators.Operator):
	def __init__(self, parent, id, pos=(-1,-1), guiPanel=None, RMSNormalize=True):
		Operators.Operator.__init__(self, parent, id, pos, guiPanel)
		self.name = "Amplitude Modulator"
		self.parameters = []
		self.parameters.append(SignalParameter(name="Modulation Depth", type=float, default = 0, range = (0, 1), unit="%"))
		self.parameters.append(SignalParameter(name="Frequency", type=float, default=1000, range = (0,5000), unit="Hz"))
		self.parameters.append(SignalParameter(name="Phase", type=float, default = 0, range = (-1, 1), unit="radians (pi)"))
		self.waveInputs.append(WaveInput(name="wave"))
		self.RMSNormalize = RMSNormalize
		self.setUpView()
		self.createParameterGUI(defaultAxes = {"xy":[(self.parameters[0], self.parameters[1])], "y":[self.parameters[2]]})
	
	def createWaveform(self, samplesPerSecond=44100, durationInSeconds=1, startAtSample=0):
		print self.waveInputs[0]
		waveToModulate = self.waveInputs[0].createWaveform(samplesPerSecond, durationInSeconds, startAtSample)
		RMS = numpy.sqrt((waveToModulate*waveToModulate).mean())
		
		freqWaveform = self.parameters[1].createWaveform(samplesPerSecond, durationInSeconds, startAtSample)
		amplitudeWaveform = self.parameters[0].createWaveform(samplesPerSecond, durationInSeconds, startAtSample)
		phaseWaveform = numpy.pi*self.parameters[2].createWaveform(samplesPerSecond, durationInSeconds, startAtSample)
		time=numpy.array([(t+startAtSample)/float(samplesPerSecond) for t in xrange(int(durationInSeconds*samplesPerSecond))])
		#print "phaseWaveform:", phaseWaveform
		modulationWave = amplitudeWaveform * numpy.sin(2*numpy.pi*freqWaveform * time + phaseWaveform)
		
		#print "ModulationWave:", modulationWave[:100]
		
		newWave = (waveToModulate)*(1+modulationWave)
		newRMS = numpy.sqrt((newWave*newWave).mean())
		newWave = (newWave * RMS/float(newRMS))
		#print "New Wave",newWave[:100]
		#print "Correcting Factor:", numpy.sqrt(RMS/float(newRMS))
		#print "Sinusoidal:", amplitudeWaveform * numpy.sin(freqWaveform * time + phaseWaveform)
		return newWave
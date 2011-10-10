import wx
import numpy
import FlowChartItems.SignalGenerators.Modulators as Modulators
from SignalParameter import SignalParameter

class Sinusoidal(Modulators.Modulator):
	"""The PureTone Carrier Signal class represents a Sinusoidal waveform.  As such, it has the parameters Frequency, Amplitude, and Phase"""
	def __init__(self, parent, id, pos=(-1,-1), guiPanel=None):
		Modulators.Modulator.__init__(self, parent, id, pos, guiPanel)
		
		self.name = "Sinusoidal\nModulation"
		self.parameters = []
		self.parameters.append(SignalParameter(name="Offset", type=float, default = 0, range = (None, None), unit=""))
		self.parameters.append(SignalParameter(name="Frequency", type=float, default=1000, range = (0,5000), unit="Hz"))
		self.parameters.append(SignalParameter(name="Amplitude", type=float, default=50, range = (0, 10), unit="V"))
		self.parameters.append(SignalParameter(name="Phase", type=float, default = 0, range = (-1, 1), unit="radians (pi)"))
		
		self.setUpView()
		self.createParameterGUI(defaultAxes = {"xy":[(self.parameters[1], self.parameters[2])], "y":[self.parameters[3]]})
	
	def changeUnitsWave(self, unit, range=None):
		self.parameters[2].setUnit(unit, range)
		self.parameterInterface.Refresh()
	def createWaveform(self, samplesPerSecond=44100, durationInSeconds=1, startAtSample=0):
		freqWaveform = self.parameters[1].createWaveform(samplesPerSecond, durationInSeconds, startAtSample)
		amplitudeWaveform = self.parameters[2].createWaveform(samplesPerSecond, durationInSeconds, startAtSample)
		phaseWaveform = numpy.pi*self.parameters[3].createWaveform(samplesPerSecond, durationInSeconds, startAtSample)
		time=numpy.array([(t+startAtSample)/float(samplesPerSecond) for t in xrange(int(durationInSeconds*samplesPerSecond))])
		#print "Sinusoidal:", amplitudeWaveform * numpy.sin(freqWaveform * time + phaseWaveform)
		return amplitudeWaveform * numpy.sin(freqWaveform * time + phaseWaveform)
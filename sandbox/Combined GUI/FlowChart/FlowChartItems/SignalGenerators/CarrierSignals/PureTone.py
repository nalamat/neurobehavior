import wx
import numpy

import FlowChartItems.SignalGenerators.CarrierSignals as CarrierSignals
from SignalParameter import SignalParameter

class PureTone(CarrierSignals.CarrierSignal):
	"""The PureTone Carrier Signal class represents a Sinusoidal waveform.  As such, it has the parameters Frequency, Amplitude, and Phase"""
	def __init__(self, parent, id, pos=(-1,-1), guiPanel=None):
		CarrierSignals.CarrierSignal.__init__(self, parent, id, pos, guiPanel)
		
		self.name = "Pure Tone"
		self.frequency = SignalParameter(name="Frequency", type=float, default=1000, range = (0,5000), unit="Hz")
		self.amplitude = SignalParameter(name="Amplitude", type=float, default=50, range = (0, 10), unit="V")
		self.phase = SignalParameter(name="Phase", type=float, default = 0, range = (-1, 1), unit="radians (pi)")
		
		self.rFrequency = SignalParameter(name="Right Ear Frequency", type=float, default=1000, range=(0,5000), unit="Hz", linkable=True)
		self.lFrequency = SignalParameter(name="Left Ear Frequency", type=float, default=1000, range=(0,5000), unit="Hz", linkable=True)
		self.rAmplitude = SignalParameter(name="Right Ear Amplitude", type=float, default=50, range = (0, 10), unit="V", linkable=True)
		self.lAmplitude = SignalParameter(name="Left Ear Amplitude", type=float, default=50, range = (0, 10), unit="V", linkable=True)
		self.rPhase = SignalParameter(name="Right Ear Phase", type=float, default = 0, range = (-1, 1), unit="radians (pi)", linkable=True)
		self.lPhase = SignalParameter(name="Left Ear Phase", type=float, default = 0, range = (-1, 1), unit="radians (pi)", linkable=True)
		
		self.monoParameters = [self.frequency, self.amplitude, self.phase]
		self.stereoParameters = self.monoParameters + [self.rFrequency, self.lFrequency, self.rAmplitude, self.lAmplitude, self.rPhase, self.lPhase]
		
		
		self.parameters = self.monoParameters
		
		self.setUpView()
		self.createParameterGUI(defaultAxes = {"xy":[(self.parameters[0], self.parameters[1])], "y":[self.parameters[2]]})
	
	def setupLink(self, linkableParam, linkedParam):
		def linkDifferenceFunc(linkableParam=linkableParam, linkedParam=linkedParam):
			return linkableParam.value - linkedParam.value
		linkableParam.bindLinkDifferenceFunc(linkDifferenceFunc)
		
	def changeUnitsWave(self, unit, range=None):
		self.amplitude.setUnit(unit, range)
		
	def setStereo(self, stereo):
		if stereo == self.stereo: return
		self.stereo = stereo
		if self.stereo: self.parameters = self.stereoParameters
		else: self.parameters = self.monoParameters
		self.setUpView()
		self.createParameterGUI(defaultAxes = {"xy":[(self.parameters[3], self.parameters[1])], "y":[self.parameters[2]]})
		self.loseFocus()
		self.gainFocus()
		
	def createWaveform(self, samplesPerSecond=44100, durationInSeconds=1, startAtSample=0):
		freqWaveform = self.parameters[0].createWaveform(samplesPerSecond, durationInSeconds, startAtSample)
		amplitudeWaveform = self.parameters[1].createWaveform(samplesPerSecond, durationInSeconds, startAtSample)
		phaseWaveform = numpy.pi * self.parameters[2].createWaveform(samplesPerSecond, durationInSeconds, startAtSample)
		time = numpy.arange(len(amplitudeWaveform))/float(samplesPerSecond)
		#print "Freq:",len(freqWaveform),freqWaveform
		#print "Ampl:", len(amplitudeWaveform),amplitudeWaveform
		#print "Phase:",len(phaseWaveform), phaseWaveform
		#print "time:",len(time),time
		wave = amplitudeWaveform * numpy.sin(2*numpy.pi*freqWaveform*time+phaseWaveform)
		"""f=open('pureAM.csv','w')
		for i in xrange(len(wave)):
			f.write(str(wave[i])+'\n')
		f.close()
		"""
		return wave
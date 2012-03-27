import wx
import numpy
import math
import scipy
import scipy.signal
import FlowChartItems.SignalGenerators.CarrierSignals as CarrierSignals
from SignalParameter import SignalParameter

class WhiteNoise(CarrierSignals.CarrierSignal):
	"""The PureTone Carrier Signal class represents a Sinusoidal waveform.  As such, it has the parameters Frequency, Amplitude, and Phase"""
	def __init__(self, parent, id, pos=(-1,-1), guiPanel=None):
		CarrierSignals.CarrierSignal.__init__(self, parent, id, pos, guiPanel)
		
		self.name = "White Noise"
		self.parameters = []
		self.parameters.append(SignalParameter(name="Center Frequency", type=float, default=1000, range = (0,5000), unit="Hz", attachable=False))
		self.parameters.append(SignalParameter(name="Bandwidth", type=float, default=50, range = (0, 150), unit="%", attachable=False, linkedParameter=self.parameters[0]))
		self.parameters.append(SignalParameter(name="Amplitude", type=float, default = 50, range = (0, 10), unit="V"))
		self.parameters.append(SignalParameter(name="Random Seed", type=int, default = 0, range = (0, 32000), unit = "", attachable=False))
		self.setUpView()
		self.createParameterGUI(defaultAxes = {"xy":[(self.parameters[0], self.parameters[1])], "y":[self.parameters[2], self.parameters[3]]})
	
	def changeUnitsWave(self, unit, range=None):
		self.parameters[2].setUnit(unit, range)
		self.parameterInterface.Refresh()
		
	def createWaveform(self, samplesPerSecond=44100, durationInSeconds=1, startAtSample=0):
		amplitudeWaveform = self.parameters[2].createWaveform(samplesPerSecond, durationInSeconds, startAtSample)
		centerFrequency = self.parameters[0].getValue()
		bandwidth =self.parameters[1].getValue()*centerFrequency
		randSeed = self.parameters[3].getValue()
		#print randSeed, type(randSeed)
		numpy.random.seed(randSeed)
		noise = (numpy.random.rand(durationInSeconds*samplesPerSecond)-.5)*2.0
		lowerFreq = (math.sqrt(bandwidth*bandwidth + 4*centerFrequency*centerFrequency) - bandwidth)/2.0
		upperFreq = lowerFreq + bandwidth
		wp = [lowerFreq/(samplesPerSecond/2.0), upperFreq/(samplesPerSecond/2.0)]
		ws = [0.9*wp[0], 1.1*wp[1]]
		b, a = b, a =scipy.signal.iirdesign(wp=wp, ws=ws, gpass=3, gstop=48, ftype='butter', output='ba')
		noise = scipy.signal.lfilter(b, a, noise)
		f = open("noise.csv","w")
		for i in xrange(len(noise)):
			f.write(str(noise[i])+'\n')
		f.close()
		f = open("amplitude.csv","w")
		for i in xrange(len(amplitudeWaveform)):
			f.write(str(amplitudeWaveform[i])+'\n')
		f.close()
		wave = amplitudeWaveform * noise
		f=open("output.csv",'w')
		for i in xrange(len(wave)):
			f.write(str(wave[i])+'\n')
		f.close()
		return amplitudeWaveform * noise
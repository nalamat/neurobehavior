#
#  Waveform.py
#  GUI
#
#  Created by spencer3 on 6/9/10.
#  Copyright (c) 2010 __MyCompanyName__. All rights reserved.
#

from SignalParameter import SignalParameter
import numpy, math

class Waveform:
	def __init__(self):
		self.frequency = SignalParameter(name="Frequency", type=float, default=5000, range = (0,30000), unit="Hz")
		self.amplitude = SignalParameter(name="Amplitude", type=float, default = 1, range = (0, 2), unit=None)
		
		self.allParameters = self.getAllParameters()
		
		for parameter in self.allParameters.values():
			parameter.bindOnSet(self.makeDirty)
		
		self.funcCallsOnDirty = []
		
		self.isDirty=self.makeDirty()
		Waveform.__init__ = None
	
	def getAllParameters(self):
		parameterDict = {}
		for variableName, variableValue in self.__dict__.iteritems():
			if isinstance(variableValue, SignalParameter):
				parameterName = variableValue.name if variableValue.name != None else variableName
				parameterDict[parameterName] = variableValue
		return parameterDict
	
	def bindOnChange(self, func):
		self.funcCallsOnDirty.append(func)
		
	def makeDirty(self, *args):
		self.isDirty=True
		for call in self.funcCallsOnDirty:
			call()
	
	def makeClean(self):
		self.isDirty=False
		
	def isDirty(self):
		return self.isDirty
		
	def rawWaveform(self, samplesPerSecond=44100, durationInSeconds=.0001):
		amplitude = self.amplitude.getValue()
		frequency = self.frequency.getValue()
		numSamples = int(math.ceil(durationInSeconds*samplesPerSecond))
		toReturn = numpy.array([amplitude * numpy.sin(2*numpy.pi * frequency * i/float(samplesPerSecond)) for i in xrange(numSamples)]) 
		self.makeClean()
		return toReturn

waveform = Waveform()
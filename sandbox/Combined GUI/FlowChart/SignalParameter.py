#
#  SignalParameter.py
#  GUI
#
#  Created by spencer3 on 6/9/10.
#  Copyright (c) 2010 __MyCompanyName__. All rights reserved.
#
import numpy

class Parameter:
	def __init__(self, name, attachable, linkedParameter):
		self.value=0
		self.attachable = attachable
		self.attachedWaveGenerator = None
		self.name = name
		self.linkedParameter = linkedParameter
	def isAttachable(self):
		return self.attachable
	def attachSignal(self, signal):
		self.attachedWaveGenerator = signal
	def detachSignal(self):
		self.attachedWaveGenerator = None	
	def isAttached(self):
		return self.attachedWaveGenerator != None
	def setUnit(self, unit, range=None):
		return
	def createWaveform(self, samplesPerSecond, durationInSeconds, startAtSample=0):
		if self.attachedWaveGenerator == None:
			return numpy.ones(samplesPerSecond*durationInSeconds) * self.value
		attachedWave = self.attachedWaveGenerator.createWaveform(samplesPerSecond, durationInSeconds, startAtSample)
		#print "Attached Wave:",attachedWave
		return numpy.ones(samplesPerSecond*durationInSeconds) * float(self.value) + attachedWave

class WaveInput(Parameter):
	def __init__(self, name, attachable=True):
		Parameter.__init__(self,name, attachable, None)
		
class SignalParameter(Parameter):
	def __init__(self, name, type, default=None, range=None, unit=None, tickInterval=None, attachable=True, linkable=False, linkedParameter=None):
		Parameter.__init__(self,name, attachable, linkedParameter)
		self.type = type
		self.default = default
		self.range = range
		self.unit = unit
		self.value = default
		self.previousValue = default
		self.tickInterval = tickInterval
		self.linkable = linkable
		self.linkActive = False
		self.linkFunc = lambda x:0
		self.boundFuncsOnGet = []
		self.boundFuncsOnSet = []
				
	def bindOnSet(self, func):
		self.boundFuncsOnSet.append(func)
	
	def bindOnGet(self, func):
		self.boundFuncsOnGet.append(func)
	
	def bindLinkDifferenceFunc(self, func):
		self.linkFunc = func
		
	def isLinkable(self):
		return self.linkable
	
	def isLinked(self):
		return self.linkActive
		
	def toggleLink(self):
		self.linkActive = not self.linkActive
		if self.linkActive: self.linkDifference=self.linkFunc()
	def getValue(self):
		for boundFunc in self.boundFuncsOnGet:
			boundFunc(self)
		return self.type(self.value)
	
	def setUnit(self, unit, range=None):
		self.unit = unit
		self.range = range
		
	def setValue(self, val):
		try:
			if self.range != None:
				if val < self.range[0] or val > self.range[1]:
					raise Exception("Value %s exceeded range %s for parameter name %s" %(str(val), str(self.range), self.name))
		except:
			raise Exception("Error setting value for parameter %s to %s" %(self.name, str(val)))
		if self.value != val:
			self.previousValue = self.value
			self.value = val
			for boundFunc in self.boundFuncsOnSet:
				boundFunc(self)				
	

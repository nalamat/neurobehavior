#
#  Axis.py
#  GUI
#
#  Created by spencer3 on 6/9/10.
#  Copyright (c) 2010 __MyCompanyName__. All rights reserved.
#

import TextInput
import CheckBox
import math

class Axis:
	def __init__(self):
		self.parameter = None
		self.attachParameter(None)
		self.logScaling = False
		self.funcsToCallOnValueChange = []
	def attachParameter(self, param):
		print "Attaching parameter",param
		oldParameter = self.parameter
		self.parameter = param
		self.updateVarsFromParameter()
		if param != None and oldParameter != self.parameter:
			for func in self.funcsToCallOnValueChange:
				self.parameter.bindOnSet(func)
			
	def updateVarsFromParameter(self):
		if self.parameter == None:
			self.name="Double-click to add a parameter"
			self.unit="None"
			self.minValue = None
			self.maxValue = None
			self.tickInterval = None
			self.currentPossibleValues = []		
		else:
			self.name = self.makeNoneEmptyString(self.parameter.name)
			self.unit = self.makeNoneEmptyString(self.parameter.unit)
			if self.parameter.range == None:
				self.minValue = ""
				self.maxValue = ""
			else:
				self.minValue = self.makeNoneEmptyString(self.parameter.range[0])
				self.maxValue = self.makeNoneEmptyString(self.parameter.range[1])
			self.tickInterval = self.parameter.tickInterval
			if self.tickInterval == None:
				self.tickInterval = (self.maxValue - self.minValue) / 10.
			self.refreshCurrentPossibleValues()
	def valueToAxisPlacement(self, value):
		minValue = self.minValue
		maxValue = self.maxValue
		toAddToEachValue = 0
		if minValue < 1 and self.logScaling: #Then we need to transform minValue to be 1 for logScaling
			toAddToEachValue = 1 - minValue
		if self.logScaling:
			minValue = math.log(minValue + toAddToEachValue)
			maxValue = math.log(maxValue + toAddToEachValue)
			value = math.log(value + toAddToEachValue)
		return (value - minValue)/float(maxValue - minValue)
		
	def saveState(self):
		import Waveform, copy
		toReturn = copy.copy(self.__dict__)
		parameterCanonicalName = None
		for paramName, param in Waveform.waveform.getAllParameters().iteritems():
			if param == self.parameter:
				parameterCanonicalName = paramName
				break
		toReturn['ParameterCanonicalName'] = parameterCanonicalName
		del toReturn['parameter']
		return toReturn
	
	def loadState(self, attributes):
		import Waveform
		for attrName, attrValue in attributes.iteritems():
			setattr(self, attrName, attrValue)
		waveform = Waveform.waveform
		if self.ParameterCanonicalName != None:
			self.parameter = waveform.allParameters[self.ParameterCanonicalName]
		else:self.parameter = None
		
	def bindOnValueChange(self, func):
		self.funcsToCallOnValueChange.append(func)
		if self.parameter != None:
			self.parameter.bindOnSet(func)

	def refreshCurrentPossibleValues(self):
		x = self.minValue
		self.currentPossibleValues = []
		while x <= self.maxValue:
			self.currentPossibleValues.append(x)
			x += self.tickInterval

	def makeNoneEmptyString(self, item):
		if item == None: return ""
		else: return item
	def getUIElements(self):
		print "Getting UIElements",self.minValue
		UIElements = []
		UIElements.append(TextInput.TextInput(name="Min Value:", defaultValue=self.minValue, validationFunction=self.parameter.type))
		UIElements.append(TextInput.TextInput(name="Max Value:", defaultValue=self.maxValue, validationFunction=self.parameter.type))
		UIElements.append(TextInput.TextInput(name="Tick Interval:", defaultValue=self.tickInterval, validationFunction = float))
		UIElements.append(CheckBox.CheckBox(name="Log Scaling:", defaultValue=self.logScaling))
		return UIElements

	def setValues(self, values):
		self.logScaling = values[-1]
		self.minValue, self.maxValue, self.tickInterval = [self.parameter.type(value) for value in values[:-1]]
		self.parameter.range=(self.minValue, self.maxValue)
		self.parameter.tickInterval=self.tickInterval
		self.refreshCurrentPossibleValues()
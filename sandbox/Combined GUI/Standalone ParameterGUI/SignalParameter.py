#
#  SignalParameter.py
#  GUI
#
#  Created by spencer3 on 6/9/10.
#  Copyright (c) 2010 __MyCompanyName__. All rights reserved.
#
import Interfaces.TextInput as TextInput

class SignalParameter:
	def __init__(self, name, type, default=None, range=None, unit=None, tickInterval=None):
		self.type = type
		self.default = default
		self.range = range
		self.name = name
		self.unit = unit
		self.value = default
		self.tickInterval = tickInterval
		self.boundFuncsOnGet = []
		self.boundFuncsOnSet = []
	
	def bindOnSet(self, func):
		self.boundFuncsOnSet.append(func)
	
	def bindOnGet(self, func):
		self.boundFuncsOnGet.append(func)
	
	def getValue(self):
		for boundFunc in self.boundFuncsOnGet:
			boundFunc(self)
		return self.value
	
	def setValue(self, val):
		try:
			if self.range != None:
				if val < self.range[0] or val > self.range[1]:
					raise Exception("Value %s exceeded range %s for parameter name %s" %(str(val), str(self.range), self.name))
		except:
			raise Exception("Error setting value for parameter %s to %s" %(self.name, str(val)))
		if self.value != val:
			self.value = val
			for boundFunc in self.boundFuncsOnSet:
				boundFunc(self)
	


import Waveform
import copy

class SoundManager:
	def __init__(self):
		self.durationInSeconds = 0.01
		self.samplesPerSecond = 44100
		self.waveform = Waveform.waveform
		self.waveformParams = self.waveform.allParameters
		self.currentValue = {}
		self.possibleValues = {} #List of different currentValues soundmanager will take on under an algorithm
		self.currentlyPlayingSound = False
		self.rawWaveformBeingPlayed = []
		self.currentValueBeingPlayed = {}
		
		self.callOnSet = []
		for paramName, param in self.waveformParams.iteritems():
			self.currentValue[paramName] = param.getValue()
		self.currentValueBeingPlayed.update(self.currentValue)
		self.rawWaveformBeingPlayed = self.waveform.rawWaveform(self.samplesPerSecond, self.durationInSeconds)
	
	def recursePossibleValues(self, index, listOfLists, dictToUpdate = None):
		if dictToUpdate == None: dictToUpdate = {}
		toReturn = []
		if index == len(listOfLists):
			return [copy.copy(dictToUpdate)]
		oldDictToUpdate = copy.copy(dictToUpdate)
		for newDict in listOfLists[index]:
			dictToUpdate.update(newDict)
			toReturn += self.recursePossibleValues(index+1, listOfLists, dictToUpdate)
			dictToUpdate = oldDictToUpdate
		return toReturn
		
	def getPossibleValues(self):
		#First turn getPossibleValues into list of lists:
		possibilities = self.possibleValues.values()
		if len(possibilities) == 0: return []
		toReturn = self.recursePossibleValues(index = 0, listOfLists = possibilities, dictToUpdate = {})
		return toReturn
		
	def addPossibleValue(self, dictOfValues):
		keys = tuple(sorted(dictOfValues.keys()))
		if keys not in self.possibleValues: self.possibleValues[keys] = []
		self.possibleValues[keys].append(dictOfValues)
		
	def bindOnSet(self, func):
		self.callOnSet.append(func)
		
	def getCurrentValue(self):
		return copy.copy(self.currentValueBeingPlayed)
	
	def getValue(self, item):
		return self.currentValueBeingPlayed.get(item)
		
	def getCurrentRawWaveform(self):
		return copy.copy(self.rawWaveformBeingPlayed)
		
	def setCurrentValue(self, dictOfValues):
		self.currentValue.update(dictOfValues)
		for paramName, value in self.currentValue.iteritems():
			self.waveformParams[paramName].setValue(value)
		if not self.currentlyPlayingSound:
			self.rawWaveformBeingPlayed = self.waveform.rawWaveform(samplesPerSecond=self.samplesPerSecond, durationInSeconds = self.durationInSeconds)
			self.currentValueBeingPlayed.update(self.currentValue)
			for func in self.callOnSet:
				func()
		else:
			raise Exception("Playing Sound not yet implemented")#Now we need to add currentValue to a queue to be executed
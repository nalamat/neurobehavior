#
#  SignalParameter.py
#  GUI
#
#  Created by spencer3 on 6/9/10.
#  Copyright (c) 2010 __MyCompanyName__. All rights reserved.
#
import numpy

class WaveInput:
	def __init__(self, name):
		self.name = name
		self.attachedWaveGenerator = None
		
	def attachSignal(self, signal):
		self.attachedWaveGenerator = signal
		
	def detachSignal(self):
		self.attachedWaveGenerator = None
	
	def isAttached(self):
		return self.attachedWaveGenerator != None
						
	def createWaveform(self, samplesPerSecond=44100, durationInSeconds=1):
		attachedWave = self.attachedWaveGenerator.createWaveform(samplesPerSecond, durationInSeconds)
		return attachedWave
	

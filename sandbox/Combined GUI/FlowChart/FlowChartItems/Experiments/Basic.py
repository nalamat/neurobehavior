import wx

import FlowChartItems.Experiments as Experiments
import WaveInput

class Basic(Experiments.Experiment):
	def __init__(self, parent, id, pos=(-1,-1), guiPanel=None):
		Experiments.Experiment.__init__(self, parent, id, pos, guiPanel)
		self.name="Basic Experiment"
		
		self.waveInputs = []
		self.waveInputs.append(WaveInput.WaveInput(name="Input"))
		self.duration=.1
		self.repeatForever=True
		self.setUpView()
		self.currentlyRunningExperiment=False
	
	def playWave(self):
		wave = self.waveInputs[0].createWaveform(durationInSeconds=self.duration)
		print wave
		
	def stopWave(self):
		pass
		
	def runExperiment(self):
        print 'running'
		self.currentlyRunningExperiment=True
		self.playWave()
	
	def stopExperiment(self):
		self.stopWave()
		self.currentlyRunningExperiment=False

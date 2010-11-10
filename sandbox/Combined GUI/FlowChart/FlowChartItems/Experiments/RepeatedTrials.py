
import wx

import FlowChartItems.Experiments as Experiments
import FlowChartItems
import WaveInput
from SignalParameter import SignalParameter
from DSPInterface import SimpleDSPInterface
import numpy

class RepeatedTrials(Experiments.Experiment):
	def __init__(self, parent, id, pos=(-1,-1), guiPanel=None):
		Experiments.Experiment.__init__(self, parent, id, pos, guiPanel)
		self.name="Trials Experiment"
		
		self.waveInputs = []
		self.waveInputs.append(WaveInput.WaveInput(name="Input"))
		
		self.trialParameter = SignalParameter(name="Number of Trials", type=int, default = 1, range = (0,10), unit="", attachable=False)
		self.durationParameter = SignalParameter(name="Duration of Trial", type=float, default=1, range=(0,5), unit="sec", attachable=False)
		self.timeBetweenTrials = SignalParameter(name="Time Between Trials", type=float, default=0.5, range=(0,5), unit="sec", attachable=False)
		
		self.parameters = [self.trialParameter, self.durationParameter, self.timeBetweenTrials]
		self.parameterYRanges = []
		
		self.setUpView()
		self.createParameterGUI(defaultAxes = {"xy":[(self.trialParameter, self.durationParameter)], "y":[self.parameters[2]]})
	
		self.currentlyRunningExperiment=False
		#self.dspManager = SimpleDSPInterface()
		
	def gainFocus(self):
		if self.hasFocus: return
		self.guiPanel.focusOn(self.parameterInterface)
		FlowChartItems.FlowChartItem.gainFocus(self)

	def playWave(self):
		trialDuration = self.durationParameter.getValue()
		numTrials = int(self.trialParameter.getValue())
		timeBetweenTrials = self.timeBetweenTrials.getValue()
		
		samplingRate = self.dspManager.getSamplingRate()
		
		wave = self.waveInputs[0].createWaveform(samplesPerSecond=samplingRate, durationInSeconds=trialDuration)
		silence = numpy.zeros(timeBetweenTrials*samplingRate)
		
		buffer = numpy.concatenate([silence, wave]*numTrials)
		
		self.dspManager.uploadBuffer(buffer)
		self.dspManager.start()
	def stopWave(self):
		self.dspManager.stop()
		
	def runExperiment(self):
		self.currentlyRunningExperiment=True
		self.playWave()
	
	def stopExperiment(self):
		self.stopWave()
		self.currentlyRunningExperiment=False

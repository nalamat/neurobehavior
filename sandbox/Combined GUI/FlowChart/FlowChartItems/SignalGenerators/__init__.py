__all__=["CarrierSignals","Modulators","Operators"]

menuName = "Signal Generator"

import wx
import FlowChart.FlowChartItems as FlowChartItems
import ParameterGUI.ParameterInterface as ParameterInterface
from SignalParameter import SignalParameter
class SignalGenerator(FlowChartItems.FlowChartItem):
	def __init__(self, parent, id, pos=(-1,-1), guiPanel=None):
		FlowChartItems.FlowChartItem.__init__(self, parent, id, pos, guiPanel)
		self.name = ""
		self.parameters = []
		self.waveInputs = []
		self.parameterYRanges = []
		self.waveInputYRanges = []
		self.titleFont = wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, "Courier")
		self.parameterFont = wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, "Courier")
		self.bmp = None
		self.borderBuffer = 5
		self.Bind(wx.EVT_PAINT, self.onPaint)
		self.attachedParameter = None
		self.parameterInterface = None

		self.samplingFrequency=44100
		self.samplingSize = 44100
		self.__currentSampleCounter = 0
		self.stereo=False
	
	def reset(self):
		self.__currentSampleCounter = 0
	
	def next(self):
		signalDuration = self.samplingSize/float(self.samplingFrequency)
		toReturn = self.createWaveform(samplesPerSecond=self.samplingFrequency, durationInSeconds=signalDuration, startAtSample=self.__currentSampleCounter)
		self.__currentSampleCounter += int(self.samplingFrequency*durationInSeconds) #Since this multiplication may not equal the desired sampling size
		return toReturn
	
	def setSamplingFrequency(self, samplingFrequency):
		self.samplingFrequency = samplingFrequency
	
	def setSamplingSize(self, samplingSize):
		self.samplingSize=samplingSize		
		
	def gainFocus(self):
		if self.hasFocus: return
		self.guiPanel.focusOn(self.parameterInterface)
		FlowChartItems.FlowChartItem.gainFocus(self)
	
	def attachParameter(self, param):
		param.attachSignal(self)
		self.attachedParameter = param
		if isinstance(param, SignalParameter):
			self.changeUnitsWave(param.unit, param.range)
		
	def detachParameter(self):
		if self.attachedParameter == None: return
		self.attachedParameter.detachSignal()
		self.attachedParameter = None
	
	def getClosestParameterToMouseEvent(self, event):
		yCoord = event.GetY()
		minDist = None
		bestXCoord, bestYCoord = None, None
		bestParam = None
		for i in xrange(len(self.parameters)):
			param = self.parameters[i]
			if param.isAttached() or not param.isAttachable(): continue
			yRange = self.parameterYRanges[i]
			midY = (yRange[0] + yRange[1])/2
			if minDist == None or (yCoord - midY)**2 < minDist:
				minDist = (yCoord - midY)**2
				bestParam = param
				bestXCoord, bestYCoord = (0, midY)
		for i in xrange(len(self.waveInputs)):
			wave = self.waveInputs[i]
			if wave.isAttached() or not wave.isAttachable(): continue
			yRange = self.waveInputYRanges[i]
			midY = (yRange[0] + yRange[1])/2
			if minDist == None or (yCoord - midY)**2 < minDist:
				minDist = (yCoord - midY)**2
				bestParam = wave
				bestXCoord, bestYCoord = (0, midY)
		return bestParam, bestXCoord, bestYCoord

		
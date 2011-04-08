__all__=["PureTone","WhiteNoise"]

menuName = "Carrier Signal"

import wx

import FlowChartItems.SignalGenerators as SignalGenerators

class CarrierSignal(SignalGenerators.SignalGenerator):
	def __init__(self, parent, id, pos=(-1,-1), guiPanel=None):
		SignalGenerators.SignalGenerator.__init__(self, parent, id, pos, guiPanel)
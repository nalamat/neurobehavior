import utilityFunctions

__all__ = utilityFunctions.moduleNames(__file__)

import wx

import FlowChartItems.SignalGenerators as SignalGenerators

class Modulator(SignalGenerators.SignalGenerator):
	def __init__(self, parent, id, pos=(-1,-1), guiPanel=None):
		SignalGenerators.SignalGenerator.__init__(self, parent, id, pos, guiPanel)
import utilityFunctions

__all__ = utilityFunctions.moduleNames(__file__)

import FlowChartItems
import wx

class Experiment(FlowChartItems.FlowChartItem):
	def __init__(self, parent, id, pos, guiPanel):
		FlowChartItems.FlowChartItem.__init__(self, parent, id, pos, guiPanel)
		self.borderBuffer = 5
		self.parameters = []
		self.waveInputs = []
		self.parameterYRanges = []
		self.waveInputYRanges = []
		self.Bind(wx.EVT_PAINT, self.onPaint)
		
	def getClosestParameterToMouseEvent(self, event):
		yCoord = event.GetY()
		minDist = None
		bestXCoord, bestYCoord = None, None
		bestInput = None
		for i in xrange(len(self.waveInputs)):
			waveInput = self.waveInputs[i]
			if waveInput.isAttached(): continue
			yRange = self.waveInputYRanges[i]
			midY = (yRange[0] + yRange[1])/2
			if minDist == None or (yCoord - midY)**2 < minDist:
				minDist = (yCoord - midY)**2
				bestInput = waveInput
				bestXCoord, bestYCoord = (0, midY)
		
		return bestInput, bestXCoord, bestYCoord

"""	def setUpView(self):
		self.waveInputYRanges = []
		width, height = self.getDesiredWidthHeight()
		self.SetSize((width, height))
		self.bmp = wx.EmptyBitmap(width, height)
		dc = wx.MemoryDC()
		dc.SelectObject(self.bmp)
		dc.SetPen(wx.Pen('Black'))
		#Now set up the Title
		dc.SetFont(self.titleFont)
		titleWidth, titleHeight = dc.GetTextExtent(self.name)
		centerWidth = width/2
		centerHeight = self.borderBuffer + 1.25*titleHeight/2
		dc.DrawText(self.name, centerWidth - titleWidth/2, centerHeight - 0.5*titleHeight)
		
		br = 1.5*titleHeight + self.borderBuffer
		
		#Now draw the params
		dc.SetFont(self.parameterFont)
		for waveInput in self.waveInputs:
			dc.SetPen(wx.Pen('Gray'))
			dc.DrawLine(1, br, width - 1, br)
			textWidth, textHeight = dc.GetTextExtent(waveInput.name)
			centerHeight = br + 1.5 * textHeight/2
			dc.DrawText(waveInput.name, self.borderBuffer, centerHeight - 0.5*textHeight)
			br += 1.5 * textHeight
			self.waveInputYRanges.append((br-1.5*textHeight, br))
"""
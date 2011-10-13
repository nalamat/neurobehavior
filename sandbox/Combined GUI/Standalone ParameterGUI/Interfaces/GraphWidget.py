#
#  GraphWidget.py
#  GUI
#
#  Created by spencer3 on 6/16/10.
#  Copyright (c) 2010 __MyCompanyName__. All rights reserved.
#

import wx
import math
import Waveform

class GraphWidget(wx.Panel):
	def __init__(self, parent, id, title, soundManager=None):
		wx.Panel.__init__(self, parent, id)
		self.soundManager = soundManager
		self.soundManager.bindOnSet(self.Refresh)
		
		self.yBorder = 10
		self.xBorder = 10
		self.Bind(wx.EVT_PAINT, self.onPaint)
		self.Bind(wx.EVT_SIZE, self.onSize)
		
		self.Show()
	def saveState(self):
		return {"WidgetClassName": "GraphWidget"}
	def loadState(self, attributes):
		for attrName, attrValue in attributes.iteritems():
			setattr(self, attrName, attrValue)
		
	def orient(self, orientation):
		pass
	def onPaint(self, event):
		
		width, height = self.GetSize()
		dc = wx.PaintDC(self)
		dc.SetPen(wx.Pen('Black'))
		#draw xAxis Line
		dc.DrawLine(self.xBorder, height/2, width - self.xBorder, height/2)
		#draw yAxis Line
		dc.DrawLine(self.xBorder, self.yBorder, self.xBorder, height - self.yBorder)
		
		rawWaveform = self.soundManager.getCurrentRawWaveform()
		maxYValue = max(rawWaveform)
		minYValue = min(rawWaveform)
		previousPoint = None
		for i in xrange(width-2*self.xBorder):
			valueToDraw = rawWaveform[int(i*len(rawWaveform)/float(width-2*self.xBorder))]
			newPoint = (i+self.xBorder, (5-valueToDraw)/(10) * (height - 2*self.yBorder) + self.yBorder)
			if previousPoint != None:
				dc.DrawLinePoint(previousPoint, newPoint)
			previousPoint = newPoint
	
	def onSize(self, event):
		self.Refresh()
		
__all__ = ["SignalGenerators", "Experiments"]

menuName = "Flow Chart Item"

import wx
import ParameterGUI.ParameterInterface as ParameterInterface
class FlowChartItem(wx.Panel):
	def __init__(self, parent, id, pos=(-1,-1), guiPanel=None):
		wx.Panel.__init__(self, parent, id, pos=pos)
		self.Bind(wx.EVT_MOUSE_EVENTS, self.handleMouseEvent)
		self.hasFocus=False
		self.guiPanel = guiPanel
		self.titleFont = wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, "Courier")
		self.parameterFont = wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, "Courier")
		
	def gainFocus(self):
		self.hasFocus=True
		self.Refresh()

	def loseFocus(self):
		self.hasFocus=False
		self.Refresh()
	def setStereo(self, stereo):
		return
	
	def createParameterGUI(self, defaultAxes = None):
		self.parameterInterface = ParameterInterface.ParameterInterface(parent=self.guiPanel, parametersToControl=self.parameters, defaultAxes=defaultAxes)
	
	def onPaint(self, event):
		dc = wx.PaintDC(self)
		width, height = self.getDesiredWidthHeight()
		#Draw a border
		if self.hasFocus: dc.SetPen(wx.Pen('Red'))
		else: dc.SetPen(wx.Pen('Black'))
		#print "Drawing Lines"
		dc.DrawBitmap(self.bmp, 0, 0,True)
				
		dc.DrawLine(1,1, width-1,1)
		dc.DrawLine(1,1, 1, height-1)
		dc.DrawLine(1, height-1, width-1, height-1)
		dc.DrawLine(width-1, 1, width-1, height -1)
		

	def getDesiredWidthHeight(self):
		width = 0
		height = 0
		dc = wx.MemoryDC()
		dc.SelectObject(wx.EmptyBitmap(512, 32))
		dc.SetFont(self.titleFont)
		titleWidth, titleHeight = dc.GetTextExtent(self.name)
		width = titleWidth
		height = titleHeight * 1.25
		dc.SetFont(self.parameterFont)
		for param in self.parameters:
			textWidth, textHeight = dc.GetTextExtent(param.name)
			width = max(textWidth, width)
			height += textHeight * 1.5
		for wave in self.waveInputs:
			textWidth, textHeight = dc.GetTextExtent(wave.name)
			width = max(textWidth, width)
			height += textHeight * 1.5
		return width+2*self.borderBuffer, height + 2*self.borderBuffer
	
	def setUpView(self):
		width, height = self.getDesiredWidthHeight()
		self.SetSize((width, height))
		self.bmp = wx.EmptyBitmap(width, height)
		dc = wx.MemoryDC()
		
		backgroundBrush = wx.Brush('White', wx.TRANSPARENT)
		dc.SetBackground(backgroundBrush)
		dc.SetBackgroundMode(wx.TRANSPARENT)
		dc.SelectObject(self.bmp)
		dc.Clear()
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
		for param in self.parameters:
			dc.SetPen(wx.Pen('Gray'))
			dc.DrawLine(1, br, width - 1, br)
			textWidth, textHeight = dc.GetTextExtent(param.name)
			centerHeight = br + 1.5 * textHeight/2
			dc.DrawText(param.name, self.borderBuffer, centerHeight - 0.5*textHeight)
			br += 1.5 * textHeight
			self.parameterYRanges.append((br-1.5*textHeight, br))
		for wave in self.waveInputs:
			dc.SetPen(wx.Pen('Gray'))
			dc.DrawLine(1, br, width - 1, br)
			textWidth, textHeight = dc.GetTextExtent(wave.name)
			centerHeight = br + 1.5 * textHeight/2
			dc.DrawText(wave.name, self.borderBuffer, centerHeight - 0.5*textHeight)
			br += 1.5 * textHeight
			self.waveInputYRanges.append((br-1.5*textHeight, br))	
			
	def handleMouseEvent(self, event):
		event.Skip()
		event.ResumePropagation(1)
		
	def runExperiment(self):
		return
	def stopExperiment(self):
		return
	
#
#  AxisWidget.py
#  GUI
#
#  Created by spencer3 on 6/9/10.
#  Copyright (c) 2010 __MyCompanyName__. All rights reserved.
#

import wx
import AxisConfig
import Waveform
import Axis
class AxisWidget(wx.Panel):
	def __init__(self, parent, id, title, axis=None, yAxis = None, xAxis = None, orientation="vertical", soundManager=None):
		wx.Panel.__init__(self, parent, id, size=(-1,-1), style=wx.NO_BORDER)
		self.soundManager = soundManager
		self.yAxis = yAxis
		self.xAxis = xAxis
		self.title = title
		if axis != None and yAxis == None and xAxis == None:
			if orientation == "vertical": self.yAxis = axis
			elif orientation == "horizontal": self.xAxis = axis
			
		self.defaultFont = wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, "Courier")
		self.Bind(wx.EVT_MOUSE_EVENTS, self.handleMouseEvent)
		self.Bind(wx.EVT_PAINT, self.onPaint)
		self.Bind(wx.EVT_SIZE, self.onSize)
		self.Bind(wx.EVT_LEFT_DCLICK, self.handleDoubleClick)
		self.Bind(wx.EVT_LEFT_DOWN, self.handleLeftClick)
		self.Bind(wx.EVT_LEFT_UP, self.handleLeftClickEnd)
		self.Bind(wx.EVT_MOTION, self.handleMouseMoving)
		
		self.soundManager.bindOnSet(self.checkForRefresh)
		#VARIABLES FOR MOUSE EVENTS
		self.shiftDown = False
		self.mouseDragged = False
		self.beginDragPosition = (None, None)
		self.motionSavePoint = (None, None)
		####
		
		self.lxDefaultBorderBuffer = 10
		self.lyDefaultBorderBuffer = 10
		self.waveform=Waveform.waveform
		
		self.finishSetup()

	def checkForRefresh(self):
		newCurrentValue = self.soundManager.getCurrentValue()
		if self.xAxis == None or self.xAxis.parameter == None:
			if self.yAxis == None or self.yAxis.parameter == None: return
			yValue = newCurrentValue[self.yAxis.parameter.name]
			if yValue == self.currentNodeValue[1]: return
			else: return self.Refresh()
		if self.yAxis == None or self.yAxis.parameter == None:
			xValue = newCurrentValue[self.xAxis.parameter.name]
			if xValue == self.currentNodeValue[0]: return
			else: return self.Refresh()
		xValue = newCurrentValue[self.xAxis.parameter.name]
		yValue = newCurrentValue[self.yAxis.parameter.name]
		if (xValue, yValue) == self.currentNodeValue: return
		else: return self.Refresh()
	def saveState(self):
		attributes = {}
		if self.yAxis == None: attributes['yAxis'] = None
		else: attributes['yAxis'] = self.yAxis.saveState()
		if self.xAxis == None: attributes['xAxis'] = None
		else: attributes['xAxis'] = self.xAxis.saveState()
		attributes['title'] = self.title
		attributes['lxDefaultBorderBuffer'] = self.lxDefaultBorderBuffer
		attributes['lyDefaultBorderBuffer'] = self.lyDefaultBorderBuffer
		attributes["WidgetClassName"] = "AxisWidget"
		
		return attributes
	
	def loadState(self, attributes):
		for attrName, attrValue in attributes.iteritems():
			setattr(self, attrName, attrValue)
		if self.xAxis != None:
			axis = Axis.Axis()
			axis.loadState(self.xAxis)
			self.xAxis = axis
		if self.yAxis != None:
			axis = Axis.Axis()
			axis.loadState(self.yAxis)
			self.yAxis = axis
		self.finishSetup()
		
	def finishSetup(self):
		self.queuedValues = []
		self.reloadAxisInfo()
	def reloadAxisInfo(self):
		self.yAxisTextWidth, self.yAxisTextHeight = self.calculateYAxisTextSpace()
		self.xAxisTextWidth, self.xAxisTextHeight = self.calculateXAxisTextSpace()
		
		self.possibleNodeValues = []
		self.possibleNodes = []
		
		self.currentNodeValue = (None, None)
		self.gridXRange = (0,0)
		self.gridYRange = (0,0)		
	
	def orient(self, orientation):
		if self.xAxis == None and orientation == "horizontal":
			self.xAxis = self.yAxis
			self.yAxis = None
		elif self.yAxis == None and orientation == "vertical":
			self.yAxis = self.xAxis
			self.xAxis = None
		else: return
		self.reloadAxisInfo()
		
	def combine(self, otherAxisWidget):		
		if otherAxisWidget.yAxis == None and otherAxisWidget.xAxis != None:
			if self.yAxis == None:
				self.yAxis = otherAxisWidget.xAxis
			else:
				self.xAxis = otherAxisWidget.xAxis
		elif otherAxisWidget.xAxis == None and otherAxisWidget.yAxis != None:
			if self.xAxis == None:
				self.xAxis = otherAxisWidget.yAxis
			else:
				self.yAxis = otherAxisWidget.yAxis
		elif otherAxisWidget.yAxis != None:
			self.yAxis = otherAxisWidget.yAxis
			self.yAxisTextWidth, self.yAxisTextHeight = otherAxisWidget.yAxisTextWidth, otherAxisWidget.yAxisTextHeight
			self.xAxis = otherAxisWidget.xAxis
			self.xAxisTextWidth, self.xAxisTextHeight = otherAxisWidget.xAxisTextWidth, otherAxisWidget.xAxisTextHeight
		else: return
		self.reloadAxisInfo()
		self.Refresh()

	def handleMouseEvent(self, event):
		event.Skip()
		#event.ResumePropagation(1)
	
	def handleMouseMoving(self, event):
		self.mouseDragged = event.LeftIsDown()
		if self.mouseDragged and self.shiftDown:
			if self.motionSavePoint == (None, None):
				self.motionSavePoint = self.beginDragPosition
			
			
			dc = wx.ClientDC(self)
			dc.BeginDrawing()

			dc.SetLogicalFunction(wx.XOR)
			dc.SetPen(wx.Pen("Gray"))
			dc.SetBrush(wx.Brush("Gray", wx.TRANSPARENT))
			
			#Erase previous rectangle
			w = self.motionSavePoint[0] - self.beginDragPosition[0]
			h = self.motionSavePoint[1] - self.beginDragPosition[1]
			dc.DrawRectangle(self.beginDragPosition[0], self.beginDragPosition[1], w, h)
			
			#Draw new rectangle
			self.motionSavePoint = event.GetPositionTuple()
			w = self.motionSavePoint[0] - self.beginDragPosition[0]
			h = self.motionSavePoint[1] - self.beginDragPosition[1]
			dc.DrawRectangle(self.beginDragPosition[0], self.beginDragPosition[1], w, h)
			
	def handleLeftClickEnd(self, event):
		if self.shiftDown: #Then USER is inputting possible nodes
			self.shiftDown = False
			if not self.mouseDragged: #Then the USER has just clicked for the possible nodes
				clickX, clickY = event.GetPositionTuple()
				indexClosestNode, closestDistance = self.getNodeClosestTo((clickX, clickY), self.possibleNodes)
				newXValue, newYValue = self.possibleNodeValues[indexClosestNode]
				
				testNoneXValue=False
				testNoneYValue=False
				if self.xAxis != None and self.xAxis.parameter != None and newXValue == self.soundManager.getValue(self.xAxis.parameter.name):
					testNoneXValue=True
				if self.yAxis != None and self.yAxis.parameter != None and newYValue == self.soundManager.getValue(self.yAxis.parameter.name):
					testNoneYValue = True
					
				try:
					self.queuedValues.remove((newXValue, newYValue))
				except ValueError:
					err=False
					if testNoneXValue:
						try:
							self.queuedValues.remove((None, newYValue))
						except:
							err = True
					if testNoneYValue:
						try:
							self.queuedValues.remove((newXValue, None))
						except:
							err=True
					if err:
						self.queuedValues.append((newXValue, newYValue))					
			else: #Then the USER has dragged a box, so we need to add multiple possible nodes
				
				beginDragX, beginDragY = self.beginDragPosition
				endDragX, endDragY = event.GetPositionTuple()
				ulCornerX = min(beginDragX, endDragX)
				ulCornerY = min(beginDragY, endDragY)
				lrCornerX = max(beginDragX, endDragX)
				lrCornerY = max(beginDragY, endDragY)
				nodeIndices = self.getNodeIndicesInBBox((ulCornerX, ulCornerY), (lrCornerX, lrCornerY), self.possibleNodes)
				for nodeIndex in nodeIndices:
					newXValue, newYValue = self.possibleNodeValues[nodeIndex]
					if ((newXValue, newYValue) not in self.queuedValues):
						self.queuedValues.append((newXValue, newYValue))
						dictToAdd = {}
						if self.yAxis != None and self.yAxis.parameter != None:
							dictToAdd[self.yAxis.parameter.name] = newYValue
						if self.xAxis != None and self.xAxis.parameter != None:
							dictToAdd[self.xAxis.parameter.name] = newXValue
						self.soundManager.addPossibleValue(dictToAdd)
			self.soundManager.getPossibleValues()
			self.motionSavePoint = (None, None)
			self.Refresh()
	def handleLeftClick(self, event):
		if len(self.possibleNodes) == 0:
			self.updatePossibleNodes()
		if self.xAxis == None and self.yAxis == None or event.ControlDown():
			event.Skip(True)
			event.ResumePropagation(1)
			return
		elif event.ShiftDown():
			self.shiftDown=True
			self.beginDragPosition = event.GetPositionTuple()
			return

	
		clickX, clickY = event.GetPositionTuple()
		indexClosestNode, closestDistance = self.getNodeClosestTo((clickX, clickY), self.possibleNodes)
		
		newXValue, newYValue = self.possibleNodeValues[indexClosestNode]
		self.setValues(newXValue, newYValue)
	
	def updatePossibleNodes(self):
		self.possibleNodes = []
		for x,y in self.possibleNodeValues:
			if self.xAxis == None:
				pixelX = self.gridXRange[0]
			else:
				pixelX = self.axisValueToPixelCoord(x, self.xAxis, self.gridXRange[0], self.gridXRange[1])
			if self.yAxis == None:
				pixelY = self.gridYRange[0]
			else:
				pixelY = self.axisValueToPixelCoord(y, self.yAxis, self.gridYRange[0], self.gridYRange[1])
			self.possibleNodes.append((pixelX, pixelY))
	
	def getNodeIndicesInBBox(self, ulCorner, lrCorner, nodeList):
		toReturn = []
		for i in xrange(len(nodeList)):
			node = nodeList[i]
			if node[0] >= ulCorner[0] and node[1] >= ulCorner[1] and node[0] <= lrCorner[0] and node[1] <= lrCorner[1]:
				toReturn.append(i)
		return toReturn
		
	def getNodeClosestTo(self, point, nodeList):
		minDistance = None
		indexToReturn = None
		for i in xrange(len(nodeList)):
			node = nodeList[i]
			distance = ((node[0]-point[0])**2+(node[1]-point[1])**2)
			if minDistance == None or distance < minDistance:
				minDistance = distance
				indexToReturn = i

		return indexToReturn, minDistance
		
	def calculateYAxisTextSpace(self):
		if self.yAxis == None: return 0,0
		dc = wx.MemoryDC()
		dc.SelectObject(wx.EmptyBitmap(512, 32))
		dc.SetFont(self.defaultFont)
		nameWidth, nameHeight = dc.GetTextExtent(self.yAxis.name)
		if self.yAxis.unit == None: unitWidth, unitHeight = 0,0
		else: unitWidth, unitHeight = dc.GetTextExtent(self.yAxis.unit)
		valueWidth = 0
		print self.yAxis.currentPossibleValues
		if (self.yAxis.currentPossibleValues != None):
			for value in self.yAxis.currentPossibleValues:
				tempWidth = dc.GetTextExtent(str(value))[0]
				if tempWidth > valueWidth: valueWidth = tempWidth
		
		return (valueWidth + 1.25*unitHeight + 1.25*nameHeight, max(nameWidth,unitWidth))
	
	def calculateXAxisTextSpace(self):
		if self.xAxis == None: return 0, 0
		dc = wx.MemoryDC()
		dc.SelectObject(wx.EmptyBitmap(512, 32))
		dc.SetFont(self.defaultFont)
		nameWidth, nameHeight = dc.GetTextExtent(self.xAxis.name)
		if self.xAxis.unit == None: unitWidth, unitHeight = 0,0
		else: unitWidth, unitHeight = dc.GetTextExtent(self.xAxis.unit)
		valueHeight = 0
		if (self.xAxis.currentPossibleValues != None):
			for value in self.xAxis.currentPossibleValues:
				tempHeight = dc.GetTextExtent(str(value))[1]
				if tempHeight > valueHeight: valueHeight = tempHeight
		
		return (max(nameWidth, unitWidth), valueHeight + 1.25*unitHeight + 1.25*nameHeight)
	
	def axisValueToPixelCoord(self, value, axis, lowPixel, highPixel):
		if axis.minValue == None or axis.maxValue == None: return (highPixel + lowPixel)/2
		pixelDelta = axis.valueToAxisPlacement(value) * (highPixel - lowPixel)
		return lowPixel + pixelDelta

	def onPaint(self, event):
		self.possibleNodes = []
		#print "Queued Values:", self.queuedValues
		width, height = self.GetSize()
		dc = wx.PaintDC(self)
		dc.SetFont(self.defaultFont)		
		dc.SetPen(wx.Pen('Black'))
		xAxisValues = []
		yAxisValues = []
		if self.yAxis != None:
			#First draw the Axis Lines
			x = self.lxDefaultBorderBuffer + self.yAxisTextWidth
			self.gridYRange = (height-self.xAxisTextHeight-self.lyDefaultBorderBuffer, self.lyDefaultBorderBuffer)
			self.gridXRange = (x, x)
			dc.DrawLine(x, height - self.xAxisTextHeight - self.lyDefaultBorderBuffer, x, self.lyDefaultBorderBuffer)
			#Next draw the Axis Title
			nameWidth, nameHeight = dc.GetTextExtent(self.yAxis.name)
			dc.DrawRotatedText(self.yAxis.name, self.lxDefaultBorderBuffer, (0.5*height - 0.5*(self.lyDefaultBorderBuffer + self.xAxisTextHeight))+nameWidth/2, 90)
			unitWidth, unitHeight = dc.GetTextExtent(self.yAxis.unit)
			dc.DrawRotatedText(self.yAxis.unit, self.lxDefaultBorderBuffer + nameHeight, (height - self.lyDefaultBorderBuffer - self.xAxisTextHeight + unitWidth)/2, 90)
			#Lastly Draw the Axis Values And Grids/Tick Marks
			lastDrawnYCoord = None

			yAxisValues = []
			for value in self.yAxis.currentPossibleValues:
				yAxisValues.append(value)
				yCoord = self.axisValueToPixelCoord(value, self.yAxis, lowPixel = height - self.xAxisTextHeight - self.lyDefaultBorderBuffer, highPixel = self.lyDefaultBorderBuffer)
				xCoord = x-2
				if self.xAxis != None: horizontalLineLength = (width - self.lxDefaultBorderBuffer - xCoord)
				else: horizontalLineLength=2
				dc.DrawLine(xCoord, yCoord, xCoord+horizontalLineLength, yCoord)
				valueWidth, valueHeight = dc.GetTextExtent(str(value))
				#print yCoord + valueHeight/2, lastDrawnYCoord
				if lastDrawnYCoord != None and yCoord + valueHeight/2 > lastDrawnYCoord: continue
				dc.DrawText(str(value), xCoord - valueWidth, yCoord - valueHeight/2)
				lastDrawnYCoord = yCoord - valueHeight/2
		if self.xAxis != None:
			width -= self.lxDefaultBorderBuffer
			#First draw the Axis Lines
			y = height - self.xAxisTextHeight - self.lyDefaultBorderBuffer
			dc.DrawLine(self.lxDefaultBorderBuffer + self.yAxisTextWidth, y, width, y)
			self.gridXRange = (self.lxDefaultBorderBuffer + self.yAxisTextWidth, width)
			#Next draw the Axis Title
			nameWidth, nameHeight = dc.GetTextExtent(self.xAxis.name)
			dc.DrawText(self.xAxis.name, (0.5*width + 0.5*(self.lxDefaultBorderBuffer + self.yAxisTextWidth) - nameWidth/2), height - self.lyDefaultBorderBuffer - self.xAxisTextHeight + nameHeight)
			unitWidth, unitHeight = dc.GetTextExtent(self.xAxis.unit)
			dc.DrawText(self.xAxis.unit, (0.5*width + 0.5*(self.lxDefaultBorderBuffer + self.yAxisTextWidth) - unitWidth/2), height - self.lyDefaultBorderBuffer - self.xAxisTextHeight + 1.25*nameHeight + unitHeight)
			#Lastly draw the Axis Values And Grids/Tick Marks
			lastDrawnXCoord = None
			xAxisValues = []
			for value in self.xAxis.currentPossibleValues:
				xCoord = self.axisValueToPixelCoord(value, self.xAxis, lowPixel = self.lxDefaultBorderBuffer + self.yAxisTextWidth, highPixel=width)
				yCoord = y+2
				xAxisValues.append(value)
				if self.yAxis != None: verticalLineLength = yCoord - self.lyDefaultBorderBuffer
				else: verticalLineLength=2
				dc.DrawLine(xCoord, yCoord, xCoord, yCoord - verticalLineLength)
				valueWidth, valueHeight = dc.GetTextExtent(str(value))
				if lastDrawnXCoord != None and xCoord - valueWidth/2 < lastDrawnXCoord: continue
				dc.DrawText(str(value), xCoord - valueWidth/2, yCoord)
				lastDrawnXCoord = xCoord + valueWidth/2
		#Now Paint all the queued values:
		for xValue, yValue in self.queuedValues:
			dc.SetBrush(wx.Brush("Gray"))
		
			if xValue == None and self.xAxis != None and self.xAxis.parameter != None:
				xValue = self.soundManager.getValue(self.xAxis.parameter.name)
			if yValue == None and self.yAxis != None and self.yAxis.parameter != None:
				yValue = self.soundManager.getValue(self.yAxis.parameter.name)
			if self.xAxis == None:
				xCoord = self.lxDefaultBorderBuffer + self.yAxisTextWidth
			else: xCoord = self.axisValueToPixelCoord(xValue, self.xAxis, lowPixel = self.lxDefaultBorderBuffer + self.yAxisTextWidth, highPixel=width)
			if self.yAxis == None:
				yCoord = height - self.xAxisTextHeight - self.lyDefaultBorderBuffer
			else: yCoord = self.axisValueToPixelCoord(yValue, self.yAxis, lowPixel = height - self.xAxisTextHeight - self.lyDefaultBorderBuffer, highPixel = self.lyDefaultBorderBuffer)
			dc.DrawCircle(xCoord, yCoord, radius = 3)
		#Now paint the currentValue:
		if self.xAxis == None or self.xAxis.parameter == None:
			xValue = None 
		else:
			xValue = self.soundManager.getValue(self.xAxis.parameter.name)
		if self.yAxis == None or self.yAxis.parameter == None:
			yValue = None
		else: yValue = self.soundManager.getValue(self.yAxis.parameter.name)
		if xValue != None or yValue != None:
			dc.SetBrush(wx.Brush("Orange"))
			if self.xAxis == None:
				xCoord = self.lxDefaultBorderBuffer + self.yAxisTextWidth
			else: xCoord = self.axisValueToPixelCoord(xValue, self.xAxis, lowPixel = self.lxDefaultBorderBuffer + self.yAxisTextWidth, highPixel=width)
			if self.yAxis == None:
				yCoord = height - self.xAxisTextHeight - self.lyDefaultBorderBuffer
			else: yCoord = self.axisValueToPixelCoord(yValue, self.yAxis, lowPixel = height - self.xAxisTextHeight - self.lyDefaultBorderBuffer, highPixel = self.lyDefaultBorderBuffer)
			dc.DrawCircle(xCoord, yCoord, radius = 3)
		self.currentNodeValue = (xValue, yValue)
		#Now calculate possible Node Values
		if len(yAxisValues) == 0: yAxisValues = [None]
		if len(xAxisValues) == 0: xAxisValues = [None]
		
		self.possibleNodeValues = []
		for xValue in xAxisValues:
			for yValue in yAxisValues:
				self.possibleNodeValues.append((xValue, yValue))
		
	def onSize(self, event):
		self.Refresh()
	
	def onParameterChange(self):
		self.yAxisTextWidth, self.yAxisTextHeight = self.calculateYAxisTextSpace()
		self.xAxisTextWidth, self.xAxisTextHeight = self.calculateXAxisTextSpace()
		print self.yAxisTextWidth
		self.Refresh()
	
	def setValues(self, newXValue, newYValue):
		dictToSet = {}
		if newXValue != None:
			dictToSet[self.xAxis.parameter.name] = newXValue
		if newYValue != None:
			dictToSet[self.yAxis.parameter.name] = newYValue
		self.soundManager.setCurrentValue(dictToSet)
		
	def handleDoubleClick(self, event):
		width, height = self.GetSize()
		windowX, windowY = self.GetScreenPosition()
		x,y = event.GetPosition()
		if self.xAxis == None:
			axisUserConfig = AxisConfig.AxisConfig(self, position=(x+windowX,y+windowY), axisToConfig=self.yAxis)
		elif self.yAxis == None:
			axisUserConfig = AxisConfig.AxisConfig(self, position=(x+windowX,y+windowY), axisToConfig=self.xAxis)
		else:
			y = height - y
			if y < x:
				axisUserConfig = AxisConfig.AxisConfig(self, position=(x+windowX, y+windowY), axisToConfig=self.xAxis)
			else:
				axisUserConfig = AxisConfig.AxisConfig(self, position=(x+windowX, y+windowY), axisToConfig=self.yAxis)
		axisUserConfig.bindOnSave(self.onParameterChange)

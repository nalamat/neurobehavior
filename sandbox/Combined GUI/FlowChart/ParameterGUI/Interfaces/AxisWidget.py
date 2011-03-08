#
#  AxisWidget.py
#  GUI
#
#  Created by spencer3 on 6/9/10.
#  Copyright (c) 2010 __MyCompanyName__. All rights reserved.
#

import wx
import AxisConfig
import Axis
class AxisWidget(wx.Panel):
	def __init__(self, parent, id, title, axis=None, yAxis = None, xAxis = None, orientation="vertical", possibleParameters=[]):
		wx.Panel.__init__(self, parent, id, size=(-1,-1), style=wx.NO_BORDER)
		self.possibleParameters = possibleParameters
		self.yAxis = yAxis
		self.xAxis = xAxis
		if self.yAxis != None:
			self.yAxis.bindOnValueChange(self.checkForRefresh)
		if self.xAxis != None:
			self.xAxis.bindOnValueChange(self.checkForRefresh)
		if axis != None:
			axis.bindOnValueChange(self.checkForRefresh)
		self.title = title
		if axis != None and yAxis == None and xAxis == None:
			if orientation == "vertical": self.yAxis = axis
			elif orientation == "horizontal": self.xAxis = axis
		
		self.oldYValue = None
		self.oldXValue = None
		
		self.defaultFont = wx.SWISS_FONT#wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, "Courier")
		self.Bind(wx.EVT_MOUSE_EVENTS, self.handleMouseEvent)
		self.Bind(wx.EVT_PAINT, self.onPaint)
		self.Bind(wx.EVT_SIZE, self.onSize)
		self.Bind(wx.EVT_LEFT_DCLICK, self.handleDoubleClick)
		self.Bind(wx.EVT_LEFT_DOWN, self.handleLeftClick)
		self.Bind(wx.EVT_LEFT_UP, self.handleLeftClickEnd)
		self.Bind(wx.EVT_MOTION, self.handleMouseMoving)
		
		#VARIABLES FOR MOUSE EVENTS
		self.shiftDown = False
		self.mouseDragged = False
		self.beginDragPosition = (None, None)
		self.motionSavePoint = (None, None)
		####
		
		self.lxDefaultBorderBuffer = 10
		self.lyDefaultBorderBuffer = 10
		self.linkBoxSize = 10
		self.finishSetup()

	def checkForRefresh(self, changedParam):
		if self.xAxis == None or self.xAxis.parameter == None:
			if self.yAxis == None or self.yAxis.parameter == None: return
			yValue = self.yAxis.parameter.getValue()
			refresh = yValue != self.oldYValue
			self.oldYValue = yValue
			if refresh: return self.Refresh()
			else: return
		if self.yAxis == None or self.yAxis.parameter == None:
			xValue = self.xAxis.parameter.getValue()
			refresh = xValue != self.oldXValue
			self.oldXValue = xValue
			if refresh: return self.Refresh()
			else: return
		xValue = self.xAxis.parameter.getValue()
		yValue = self.yAxis.parameter.getValue()
		refresh = (xValue, yValue) == (self.oldXValue, self.oldYValue)
		self.oldxValue, self.oldYValue = xValue, yValue
		if not refresh: return
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
			otherAxisWidget.xAxis.bindOnValueChange(self.checkForRefresh)
			if self.yAxis == None:
				self.yAxis = otherAxisWidget.xAxis
			else:
				self.xAxis = otherAxisWidget.xAxis
		elif otherAxisWidget.xAxis == None and otherAxisWidget.yAxis != None:
			otherAxisWidget.yAxis.bindOnValueChange(self.checkForRefresh)
			if self.xAxis == None:
				self.xAxis = otherAxisWidget.yAxis
			else:
				self.yAxis = otherAxisWidget.yAxis
		elif otherAxisWidget.yAxis != None:
			otherAxisWidget.yAxis.bindOnValueChange(self.checkForRefresh)
			otherAxisWidget.xAxis.bindOnValueChange(self.checkForRefresh)			
			self.yAxis = otherAxisWidget.yAxis
			self.yAxisTextWidth, self.yAxisTextHeight = otherAxisWidget.yAxisTextWidth, otherAxisWidget.yAxisTextHeight
			self.xAxis = otherAxisWidget.xAxis
			self.xAxisTextWidth, self.xAxisTextHeight = otherAxisWidget.xAxisTextWidth, otherAxisWidget.xAxisTextHeight
		else: return
		self.reloadAxisInfo()
		self.Refresh()

	def handleMouseEvent(self, event):
		event.Skip()
		event.ResumePropagation(1)
	
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
				if self.xAxis != None and self.xAxis.parameter != None and newXValue == self.xAxis.parameter.getValue():
					testNoneXValue=True
				if self.yAxis != None and self.yAxis.parameter != None and newYValue == self.yAxis.parameter.getValue():
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
			self.motionSavePoint = (None, None)
			self.Refresh()
	def handleLeftClick(self, event):
		print "Got left button press AxisWidget", event.ControlDown()
		if len(self.possibleNodes) == 0:
			self.updatePossibleNodes()
		if (self.xAxis == None and self.yAxis == None) or event.ControlDown():
			event.Skip(True)
			event.ResumePropagation(1)
			return
		elif event.ShiftDown():
			self.shiftDown=True
			self.beginDragPosition = event.GetPositionTuple()
			return

	
		clickX, clickY = event.GetPositionTuple()
		if not self.clickLinkBox((clickX, clickY)):
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
		#print self.yAxis.currentPossibleValues
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

	def clickLinkBox(self, click):
		x, y = click
		if self.yAxis != None and self.yAxis.parameter != None and self.yAxis.parameter.isLinkable():
			if (x >= self.lxDefaultBorderBuffer and x <= self.lxDefaultBorderBuffer + self.linkBoxSize):
				if (y >= self.lyDefaultBorderBuffer and y <= self.lyDefaultBorderBuffer + self.linkBoxSize):
					self.yAxis.parameter.toggleLink()
					self.Refresh()
					return True
		if self.xAxis != None and self.xAxis.parameter != None and self.xAxis.parameter.isLinkable():
			if (x >= self.xAxisLinkBox[0][0] and x <= self.xAxisLinkBox[0][1]):
				if (y >= self.xAxisLinkBox[1][0] and y <= self.xAxisLinkBox[1][1]):
					self.xAxis.parameter.toggleLink()
					self.Refresh()
					return True
		return False
								
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
			self.yAxis.updateVarsFromParameter()
			self.yAxisTextWidth, self.yAxisTextHeight = self.calculateYAxisTextSpace()
			if self.yAxis.parameter.isLinkable():
				#Then draw a link box (should be a bitmap eventually)
				dc.DrawRectangle(x=self.lxDefaultBorderBuffer, y=self.lyDefaultBorderBuffer, width=self.linkBoxSize, height=self.linkBoxSize)
				if self.yAxis.parameter.isLinked():
					dc.DrawCheckMark(x=self.lxDefaultBorderBuffer+2, y=self.lyDefaultBorderBuffer, width=self.linkBoxSize-4, height=self.linkBoxSize-4)
				linkBoxOffset = self.linkBoxSize
				self.yAxisLinkBox = [(self.lxDefaultBorderBuffer, self.lxDefaultBorderBuffer+self.linkBoxSize), (self.lyDefaultBorderBuffer, self.lyDefaultBorderBuffer+self.linkBoxSize)]
			else: linkBoxOffset = 0
			x = self.lxDefaultBorderBuffer + self.yAxisTextWidth
			self.gridYRange = (height-self.xAxisTextHeight-self.lyDefaultBorderBuffer, self.lyDefaultBorderBuffer + linkBoxOffset)
			self.gridXRange = (x, x)
			dc.DrawLine(x, self.gridYRange[0],  x, self.gridYRange[1])
			#Next draw the Axis Title
			#print "Drawing axis title", self.yAxis.name, self.yAxis.unit
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
			self.xAxis.updateVarsFromParameter()
			self.xAxisTextWidth, self.xAxisTextHeight = self.calculateXAxisTextSpace()
			width -= self.lxDefaultBorderBuffer
			#First draw the Axis Lines
			if self.xAxis.parameter.isLinkable():
				dc.DrawRectangle(x=width - self.linkBoxSize, y=height - self.xAxisTextHeight, width=self.linkBoxSize, height=self.linkBoxSize)
				self.xAxisLinkBox = [(width - self.linkBoxSize, width),(height - self.xAxisTextHeight, height - self.xAxisTextHeight + self.linkBoxSize)]
				if self.xAxis.parameter.isLinked():
					dc.DrawCheckMark(x=width - self.linkBoxSize + 2, y=height - self.xAxisTextHeight, width=self.linkBoxSize-4, height=self.linkBoxSize-4)
				linkBoxOffset = self.linkBoxSize
			else: linkBoxOffset = 0
			width -= linkBoxOffset
			
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
				xValue = self.xAxis.parameter.getValue()
			if yValue == None and self.yAxis != None and self.yAxis.parameter != None:
				yValue = self.yAxis.parameter.getValue()
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
			xValue = self.xAxis.parameter.getValue()
		if self.yAxis == None or self.yAxis.parameter == None:
			yValue = None
		else: yValue = self.yAxis.parameter.getValue()
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
	
	def attachYParameter(self, param):
		self.yAxis.attachParameter(param)
		self.onParameterChange()
	def attachXParameter(self, param):
		self.xAxis.attachParameter(param)
		self.onParameterChange()
	def onParameterChange(self):
		print "On Parameter Change!"
		self.yAxisTextWidth, self.yAxisTextHeight = self.calculateYAxisTextSpace()
		self.xAxisTextWidth, self.xAxisTextHeight = self.calculateXAxisTextSpace()
		#print self.yAxisTextWidth
		self.Refresh()
	
	def setValues(self, newXValue, newYValue):
		if newXValue != None:
			self.xAxis.parameter.setValue(newXValue)
		if newYValue != None:
			self.yAxis.parameter.setValue(newYValue)
		self.Refresh()
		
	def handleDoubleClick(self, event):
		width, height = self.GetSize()
		windowX, windowY = self.GetScreenPosition()
		x,y = event.GetPosition()
		if self.xAxis == None:
			axisUserConfig = AxisConfig.AxisConfig(self, position=(x+windowX,y+windowY), axisToConfig=self.yAxis, possibleParameters = self.possibleParameters)
		elif self.yAxis == None:
			axisUserConfig = AxisConfig.AxisConfig(self, position=(x+windowX,y+windowY), axisToConfig=self.xAxis, possibleParameters=self.possibleParameters)
		else:
			y = height - y
			if y < x:
				axisUserConfig = AxisConfig.AxisConfig(self, position=(x+windowX, y+windowY), axisToConfig=self.xAxis,possibleParameters=self.possibleParameters)
			else:
				axisUserConfig = AxisConfig.AxisConfig(self, position=(x+windowX, y+windowY), axisToConfig=self.yAxis,possibleParameters=self.possibleParameters)
		axisUserConfig.bindOnSave(self.onParameterChange)

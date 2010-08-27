#
#  ParameterInterface.py
#  GUI
#
#  Created by spencer3 on 6/11/10.
#  Copyright (c) 2010 __MyCompanyName__. All rights reserved.
#

import wx
import Interfaces.AxisWidget as AxisWidget
import Interfaces.Axis as Axis
import Interfaces.GraphWidget as GraphWidget
import Interfaces.InterfaceLayoutWidget as InterfaceWidget
import WidgetLoader

class ParameterInterface(wx.Panel):
	def __init__(self, parent, title="", parametersToControl=[], defaultAxes=None):
		wx.Panel.__init__(self, parent)
		self.title = title
		self.parametersToControl = parametersToControl
		self.Bind(wx.EVT_RIGHT_DOWN, self.rightButtonMenu)
		self.Bind(wx.EVT_LEFT_DOWN, self.leftButton)
		
		self.widgets = []
		self.shownWidgets = []
		
		self.gridSizer = wx.GridBagSizer()
		#self.gridSizer.Add(xyGrid, (2,0), span=(1,1), flag=wx.EXPAND)
		self.gridSizer.Layout()
		self.SetSizer(self.gridSizer)
		self.numRows = 6
		self.numCols = 8
		for row in xrange(self.numRows):
			self.gridSizer.AddGrowableRow(row)
		for col in xrange(self.numCols):
			self.gridSizer.AddGrowableCol(col)
		if defaultAxes != None:
			xyAxes = defaultAxes.get('xy',[])
			yAxes = defaultAxes.get('y',[])
			curCol = 0
			curRow = 0
			for xParam, yParam in xyAxes:
				if curCol + 2 > self.numCols:
					curCol = 0
					curRow += 2
				if curCol + 2 > self.numRows: break
				widget = AxisWidget.AxisWidget(self, wx.ID_ANY, title="Widget", yAxis=Axis.Axis(), xAxis=Axis.Axis(), possibleParameters = self.parametersToControl)
				widget.attachYParameter(yParam)
				widget.attachXParameter(xParam)
				rowspan = 2
				colspan = 2
				self.widgets.append(widget)
				self.shownWidgets.append((curCol, curRow, (colspan, rowspan)))
				self.gridSizer.Add(widget, (curRow, curCol), span=(rowspan, colspan), flag=wx.EXPAND)
				curCol += colspan
			for yParam in yAxes:
				if curCol > self.numCols:
					curCol = 0
					curRow += 2
				if curRow + 2 > self.numRows: break
				widget = AxisWidget.AxisWidget(self, wx.ID_ANY, title="Widget", yAxis=Axis.Axis(), possibleParameters=self.parametersToControl)
				widget.attachYParameter(yParam)
				rowspan=2
				colspan=1
				self.widgets.append(widget)
				self.shownWidgets.append((curCol, curRow, (colspan, rowspan)))
				self.gridSizer.Add(widget, (curRow, curCol), span=(rowspan, colspan), flag=wx.EXPAND)	
				curCol += colspan
		self.Show(False)
		self.Show(True)
		self.Refresh()
	def leftButton(self, event):
		#print "PI Left Button:",event.GetPosition()
		if event.ControlDown(): self.rightButtonMenu(event)
		
	def rightButtonMenu(self, event):
		menu = wx.Menu()
		UIMenu = wx.Menu()
		UIMenu.Append(301, "Axis")
		UIMenu.Append(302, "Signal View")
		self.Bind(wx.EVT_MENU, self.onAddAxis, id=301)
		self.Bind(wx.EVT_MENU, self.onAddSignal, id=302)
		
		menu.AppendSubMenu(UIMenu, 'Add')
		self.PopupMenu(menu, event.GetPosition())
		menu.Destroy()
	
	def placeWidget(self, widget):
		frame = wx.Frame(None, wx.ID_ANY, "Widget Placement")
		interfacePanel = InterfaceWidget.InterfaceLayoutWidget(frame, wx.ID_ANY, self.numCols, self.numRows, self.shownWidgets)
		def getLayoutValues(self=self, widget=widget, interfacePanel=interfacePanel, frame=frame):
			col, row, (colspan, rowspan) = interfacePanel.getSelectedRange()
			item = None
			window = None
			for rowNum in xrange(row, row+rowspan,1):
				for colNum in xrange(col, col+colspan,1):
					item = self.gridSizer.FindItemAtPosition((rowNum, colNum))	
					if item != None:
						window = item.GetWindow()
						break
				if item != None: break
			if item != None:
				window.combine(widget)
				originalRow, originalCol = item.GetPos()
				originalRowspan, originalColspan = item.GetSpan()
				newCol = min(originalCol, col)
				newRow = min(originalRow, row)
				newColspan = max(originalCol+originalColspan - newCol, col+colspan - newCol)
				newRowspan = max(originalRow + originalRowspan - newRow, row+rowspan - newRow)
				item.SetPos((newRow, newCol))
				item.SetSpan((newRowspan, newColspan))
				for i in xrange(len(self.shownWidgets)):
					c, r, (cs, rs) = self.shownWidgets[i]
					if c == originalCol and r == originalRow:
						self.shownWidgets[i] = newCol, newRow, (newColspan, newRowspan)
						break
			else:
				if colspan > rowspan: widget.orient("horizontal")
				else: widget.orient("vertical")
				#Just assume that there are no conflicts with existing widget
				self.widgets.append(widget)
				self.shownWidgets.append((col, row, (colspan, rowspan)))
				self.gridSizer.Add(widget, (row, col), span=(rowspan, colspan), flag=wx.EXPAND)
			#self.Show(False)
			self.gridSizer.Layout()
			#self.Show(True)
			self.Refresh()
			frame.Close()
		frame.SetSize(interfacePanel.getSize())
		frame.Center()
		interfacePanel.bindFunc(getLayoutValues)
		frame.Show()
		
	def onAddAxis(self, event):
		widgetToAdd = AxisWidget.AxisWidget(self, wx.ID_ANY, title="Widget", yAxis=Axis.Axis(), possibleParameters = self.parametersToControl)
		self.placeWidget(widgetToAdd)
				
	def onAddSignal(self, event):
		widgetToAdd = GraphWidget.GraphWidget(self, wx.ID_ANY, title="Signal", possibleParameters=self.parametersToControl)
		self.placeWidget(widgetToAdd)
		
	def saveState(self):
		importantElements = {}
		importantElements["widgets"] = []
		for widget in self.widgets:
			importantElements["widgets"].append(widget.saveState())
		savedAttributes = {}
		savedAttributes["shownWidgets"] = self.shownWidgets
		savedAttributes["numRows"] = self.numRows
		savedAttributes["numCols"] = self.numCols
		importantElements["Attributes"] = savedAttributes
		return importantElements
	
	def loadState(self, importantElements):
		for widget in self.widgets:
			self.gridSizer.Hide(widget)
		self.widgets = []
		self.shownWidgets = []
		self.gridSizer.Clear()
		self.Show(False)
		for attrName, attrValue in importantElements["Attributes"].iteritems():
			setattr(self, attrName, attrValue)
		widgets = importantElements["widgets"]
		for widget in widgets:
			self.widgets.append(WidgetLoader.load(self, wx.ID_ANY, widget, self.soundManager))
		for i in xrange(len(self.widgets)):
			widget = self.widgets[i]
			c, r, (cs, rs) = self.shownWidgets[i]
			self.gridSizer.Add(widget, (r, c), span =(rs, cs), flag=wx.EXPAND)
		self.gridSizer.Layout()
		self.Show(True)
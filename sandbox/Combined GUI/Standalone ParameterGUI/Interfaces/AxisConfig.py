#
#  AxisConfig.py
#  GUI
#
#  Created by spencer3 on 6/9/10.
#  Copyright (c) 2010 __MyCompanyName__. All rights reserved.
#

import wx
import Waveform

class AxisConfig(wx.Frame):
	def __init__(self, parentWidget, position, axisToConfig):
		wx.Frame.__init__(self, parentWidget, wx.ID_ANY, "Axis Config", pos=position, size=(-1,200))
		self.callOnSave = []
		
		self.axisToConfig = axisToConfig
		self.currentParameter = self.axisToConfig.parameter #Actually should be parameter of current axis
				
		waveform = Waveform.waveform
		self.parameterDict = waveform.allParameters
		parameterNames = self.parameterDict.keys()
		
		comboBoxWidth = 2*self.maxWidth(parameterNames)
		
		parameterSelectorText = wx.StaticText(self,wx.ID_ANY, "Parameter:")
		parameterSelector = wx.ComboBox(self, wx.ID_ANY, self.currentParameter.name if self.currentParameter != None else "", choices=parameterNames, size=(comboBoxWidth,50), style=wx.CB_READONLY)
		
		self.parameterConfigPanels = {}
		self.parameterConfig = self.createUIPanel(self.currentParameter)
		
		self.gs = wx.GridBagSizer(hgap=5)
		self.gs.Add(parameterSelectorText, pos = (0,0), flag=wx.ALIGN_LEFT)
		self.gs.Add(parameterSelector, pos = (0,1), flag=wx.ALIGN_LEFT)
		self.gs.Add(self.parameterConfig, (1,0), span=(1, 2))
		self.SetSizer(self.gs)

		self.Bind(wx.EVT_COMBOBOX, self.newParamSelected, parameterSelector)
		
		self.Show()
	
	def bindOnSave(self, func):
		self.callOnSave.append(func)
	def maxWidth(self, listOfStrings):
		width = 0
		dc = wx.MemoryDC()
		dc.SelectObject(wx.EmptyBitmap(512, 32))
		for string in listOfStrings:
			strWidth = dc.GetTextExtent(string)[0]
			if strWidth > width:
				width = strWidth
		return width

	def newParamSelected(self, event):
		parameterSelected = event.GetString()
	
		newParameter = self.parameterDict[parameterSelected]
		if self.currentParameter == None or newParameter.name != self.currentParameter.name:
			if self.currentParameter != None: print newParameter.name, self.currentParameter.name
			else: print newParameter.name, None
			self.axisToConfig.attachParameter(newParameter)
		self.gs.Detach(self.parameterConfig)
		self.parameterConfig.Show(False)
		self.gs.Layout()
		if newParameter in self.parameterConfigPanels:
			self.gs.Add(self.parameterConfigPanels[newParameter], (1,0), span=(1,2))
			self.parameterConfig = self.parameterConfigPanels[newParameter]
			print "Should be drawing a previous Parameter Config!"
		else:
			"""
			self.parameterConfigPanels[newParameter] = wx.Panel(self, wx.ID_ANY)
			sizer = wx.BoxSizer(wx.VERTICAL)
			for UI in self.axisToConfig.getUIElements():
				widget = UI.wxWidget(self.parameterConfigPanels[newParameter])
				sizer.Add(widget, 1)
			
			buttonPanel = wx.Panel(self.parameterConfigPanels[newParameter], wx.ID_ANY)
			saveButton = wx.Button(buttonPanel, wx.ID_ANY, label="Save")
			cancelButton = wx.Button(buttonPanel, wx.ID_ANY, label="Cancel")
			buttonSizer = wx.GridSizer(rows=1, cols=2)
			def saveSelectionLambda(event, newParameter=newParameter):
				return self.saveSelection(event, newParameter)
			def cancelSelectionLambda(event):
				return self.cancelSelection(event)
			buttonSizer.Add(saveButton, 0, flag = wx.ALIGN_RIGHT)
			buttonSizer.Add(cancelButton, 1, flag = wx.ALIGN_LEFT)
			buttonSizer.Layout()
			buttonPanel.SetSizer(buttonSizer)
			sizer.Add(buttonPanel, 10)
			self.parameterConfigPanels[newParameter].SetSizer(sizer)
			"""
			self.parameterConfigPanels[newParameter] = self.createUIPanel(newParameter)
			self.gs.Add(self.parameterConfigPanels[newParameter], (1,0), span=(1,2))
			self.parameterConfig = self.parameterConfigPanels[newParameter]
		print "Trying to draw paramConfig Window"
		self.gs.Layout()
		self.parameterConfig.Show(False)
		self.parameterConfig.Show(True)
	
	def createUIPanel(self, newParameter):
		panel = wx.Panel(self, wx.ID_ANY)
		if newParameter == None: return panel
		sizer = wx.BoxSizer(wx.VERTICAL)
		widgets = []
		for UI in self.axisToConfig.getUIElements():
			widget = UI.wxWidget(panel)
			sizer.Add(widget, 1)
			widgets.append(UI)
		
		buttonPanel = wx.Panel(panel, wx.ID_ANY)
		saveButton = wx.Button(buttonPanel, wx.ID_ANY, label="Save")
		cancelButton = wx.Button(buttonPanel, wx.ID_ANY, label="Cancel")
		buttonSizer = wx.GridSizer(rows=1, cols=2)
		def saveSelectionLambda(event, newParameter=newParameter, widgets=widgets):
			print "Lambda function called"
			return self.saveSelection(event, newParameter, widgets)
		def cancelSelectionLambda(event):
			return self.cancelSelection(event)
		saveButton.Bind(wx.EVT_BUTTON, saveSelectionLambda)
		cancelButton.Bind(wx.EVT_BUTTON, cancelSelectionLambda)
			
		buttonSizer.Add(saveButton, 0, flag = wx.ALIGN_RIGHT)
		buttonSizer.Add(cancelButton, 1, flag = wx.ALIGN_LEFT)
		buttonSizer.Layout()
		buttonPanel.SetSizer(buttonSizer)
		
		sizer.Add(buttonPanel, 1)
		panel.SetSizer(sizer)
		return panel

	def saveSelection(self, event, newParameter, widgets):
		values = [UI.GetValue() for UI in widgets]
		
		print "Saving Selection", values
		self.axisToConfig.setValues(values)
		self.currentParameter = newParameter
		for call in self.callOnSave:
			call()
		self.Close()
	
	def cancelSelection(self, event):
		self.axisToConfig.attachParameter(self.currentParameter)
		self.Close()
#
#  UserInterface.py
#  GUI
#
#  Created by spencer3 on 6/9/10.
#  Copyright (c) 2010 __MyCompanyName__. All rights reserved.
#

import wx
from wx.lib.agw import aui
import ParameterInterface
import os
import cPickle

class UserInterface(wx.Panel):
	def __init__(self, parent, soundManager):
		wx.Panel.__init__(self, parent)
		self.soundManager = soundManager
		self.workspace = aui.AuiNotebook(self)
		sizer=wx.BoxSizer()
		sizer.Add(self.workspace, 1, wx.EXPAND)
		
		self.currentDefaultPageNumber = -1
		self.defaultPageNumberAdjustment = 0
		self.tabs = []
		
		self.SetSizer(sizer)
		
		self.newTab(parent)
		
	def saveCurrentTab(self):
		interface = self.workspace.GetPage(self.currentDefaultPageNumber)
		toPickle = interface.saveState()
		import cPickle
		dialog = wx.FileDialog(self, "Save As...", defaultDir = "Templates", style=wx.FD_SAVE)
		if dialog.ShowModal() == wx.ID_OK:
			outputFile = dialog.GetFilename()
			if '.' not in outputFile: outputFile += '.tmplt'
			outputDirectory = dialog.GetDirectory()
			cPickle.dump(toPickle, open(os.path.join(outputDirectory, outputFile), 'w'))
	
	def loadCurrentTab(self):
		interface = self.workspace.GetPage(self.currentDefaultPageNumber)
		dialog = wx.FileDialog(self, "Load Template", defaultDir = "Templates", style=wx.FD_OPEN)
		if dialog.ShowModal() == wx.ID_OK:
			fName = dialog.GetPath()
			toLoad = cPickle.load(open(fName, 'r'))
			interface.loadState(toLoad)
			self.workspace.SetPageText(self.currentDefaultPageNumber, interface.title)
	def newTab(self, parent):
		self.currentDefaultPageNumber += 1
		self.tabs.append(ParameterInterface.ParameterInterface(self.workspace, title='default' + '-%i' %(self.currentDefaultPageNumber) if self.currentDefaultPageNumber > 0 else 'default', soundManager = self.soundManager))
		self.workspace.AddPage(self.tabs[-1], self.tabs[-1].title)
		self.workspace.SetSelection(len(self.tabs)-1)
		self.workspace.SetRenamable(len(self.tabs)-1, True)
		
	def closeTab(self, tabNum=None):
		if tabNum == None:
			tabNum = self.workspace.GetSelection()
		if tabNum != 0:
			self.workspace.SetSelection(tabNum-1)
		elif len(self.tabs) > 1:
			self.workspace.SetSelection(tabNum+1)
		if tabNum + self.defaultPageNumberAdjustment == self.currentDefaultPageNumber: self.currentDefaultPageNumber -= 1
		else: self.defaultPageNumberAdjustment += 1
		self.workspace.DeletePage(tabNum)
		del self.tabs[tabNum]
		
	def numTabs(self):
		return self.workspace.GetPageCount()
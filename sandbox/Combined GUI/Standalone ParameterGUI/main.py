#
#  main.py
#  GUI
#
#  Created by spencer3 on 6/9/10.
#  Copyright (c) 2010 __MyCompanyName__. All rights reserved.
#

import UserInterface
import Waveform
import SoundManager
import wx

class RootWindow(wx.Frame):
	def __init__(self, parent, id, title):
		self.soundManager = SoundManager.SoundManager()
		wx.Frame.__init__(self, parent, id, title)
		
		self.createMenuBar()
		
		self.userInterface = UserInterface.UserInterface(self, soundManager=self.soundManager)

		self.Centre()
		self.Show(True)

	#def createToolbar(self):
	#	toolbar = self.CreateToolBar()
	#	toolbar.AddLabelTool(wx.ID_ANY, "Run", bima
	
	def createMenuBar(self):
		menubar = wx.MenuBar()
		file = wx.Menu()
		tab = wx.MenuItem(file, 1, 'New &Tab\tCtrl+T')
		closeTab = wx.MenuItem(file, 2, '&Close Tab\tCtrl+W')
		saveTab = wx.MenuItem(file, 5, '&Save Template\tCtrl+S')
		loadTab = wx.MenuItem(file, 6, "&Load Template\tCtrl+O")
		runAlgorithm = wx.MenuItem(file, 4, 'Auto Mode')
		
		quit = wx.MenuItem(file, 3, '&Quit\tCtrl+Q')
		
		self.Bind(wx.EVT_MENU, self.onQuit, id=3)
		self.Bind(wx.EVT_MENU, self.closeTab, id=2)
		self.Bind(wx.EVT_MENU, self.newTab, id=1)
		self.Bind(wx.EVT_MENU, self.runAlgorithm, id=4)
		self.Bind(wx.EVT_MENU, self.saveTab, id=5)
		self.Bind(wx.EVT_MENU, self.loadTab, id=6)
		
		file.AppendItem(tab)
		file.AppendItem(closeTab)
		file.AppendItem(saveTab)
		file.AppendItem(loadTab)
		file.AppendItem(runAlgorithm)
		
		file.AppendItem(quit)
		menubar.Append(file, '&File')
		
		"""
		widget = wx.Menu()
		axisWidget = wx.MenuItem(widget, 1, "Axis")
		graphWidget = wx.MenuItem(widget, 2, "Signal View")
		self.Bind(wx.EVT_MENU, self.addAxis, id=1)
		self.Bind(wx.EVT_MENU, self.addSignalView, id=2)
		menubar.Append(widget, "&Widgets")
		"""
		self.SetMenuBar(menubar)
		
	def saveTab(self, event):
		self.userInterface.saveCurrentTab()
	
	def loadTab(self, event):
		self.userInterface.loadCurrentTab()
		
	def newTab(self, event):
		self.userInterface.newTab(self)
	
	def closeTab(self, event):
		if self.userInterface.numTabs() == 0: self.onQuit(event)
		self.userInterface.closeTab()
	
	def runAlgorithm(self, event):
		import time, random
		possibleValues = self.soundManager.getPossibleValues()
		print "PossibleValues:",possibleValues
		random.shuffle(possibleValues)
		for value in possibleValues:
			self.soundManager.setCurrentValue(value)
			for i in xrange(100000):
				wx.Yield()
	def showWaveForm(self, event):
		from Interfaces import GraphWidget
		newWindow = wx.Frame(None, -1, "Signal")
		graph = GraphWidget.GraphWidget(parent=newWindow, id=-1, title="wave")
		
	def onQuit(self, event):
		self.Close()
app = wx.App(False)
RootWindow(None, -1, "Aural GUI")
app.MainLoop()
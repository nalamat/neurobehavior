import sys
sys.path.append("FlowChart")
sys.path.append("C:/Documents and Settings/admin_behavior/Desktop/testing/src")
sys.path.append("DSPManager")
import wx
import FlowChart.FlowChart as FlowChart
import ParameterGUIManager

class RootWindow(wx.Frame):
	def __init__(self, parent, id, title):
		wx.Frame.__init__(self, parent, id, title)
		
		self.splitView = wx.SplitterWindow(self, id, size=(800,600), style=wx.SP_BORDER)
		guiManager = ParameterGUIManager.ParameterGUIManager(self.splitView, wx.ID_ANY)
		
		self.flowChart = FlowChart.FlowChart(self.splitView, wx.ID_ANY, guiPanel=guiManager)
		
		self.setupMenu()
		self.splitView.SplitHorizontally(guiManager, self.flowChart, 300)
		self.splitView.SetSashGravity(0.5)
		self.splitView.SetMinimumPaneSize(10)
		self.Show(True)
	
	def setupMenu(self):
		menubar = wx.MenuBar()
		file = wx.Menu()
		saveLayout = wx.MenuItem(file, 5, '&Save Layout\tCtrl+S')
		loadLayout = wx.MenuItem(file, 6, "&Open Layout\tCtrl+O")
		quit = wx.MenuItem(file, 3, '&Quit\tCtrl+Q')
		
		self.Bind(wx.EVT_MENU, self.onQuit, id=3)
		self.Bind(wx.EVT_MENU, self.saveLayout, id=5)
		self.Bind(wx.EVT_MENU, self.loadLayout, id=6)
		
		file.AppendItem(saveLayout)
		file.AppendItem(loadLayout)		
		file.AppendItem(quit)
		menubar.Append(file, '&File')

		self.SetMenuBar(menubar)
	
	def onQuit(self, event):
		self.Close()

	def saveLayout(self, event):
		self.flowChart.save()
	
	def loadLayout(self, event):
		self.flowChart.load()
		
if __name__ == "__main__":
	app = wx.App(False)
	RootWindow(None, -1, "Combined GUI")
	app.MainLoop()
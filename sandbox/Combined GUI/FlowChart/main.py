import wx
import FlowChart

class RootWindow(wx.Frame):
	def __init__(self, parent, id, title):
		wx.Frame.__init__(self, parent, id, title)
		
		self.flowChart = FlowChart.FlowChart(self, wx.ID_ANY)
		
		self.sizer = wx.GridBagSizer()
		self.sizer.AddGrowableRow(0)
		self.sizer.AddGrowableCol(0)
		self.sizer.Add(self.flowChart, (0,0), flag=wx.EXPAND)
		self.sizer.Layout()
		
		self.SetSizer(self.sizer)
		self.Centre()
		self.Show(True)

	
if __name__ == "__main__":
	app = wx.App(False)
	RootWindow(None, -1, "Flowchart GUI")
	app.MainLoop()
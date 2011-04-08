import wx

class ParameterGUIManager(wx.Panel):
	def __init__(self, parent, id):
		wx.Panel.__init__(self, parent, id)
		self.sizer = wx.BoxSizer()
		self.SetSizer(self.sizer)
				
	def focusOn(self, child):
		for object in self.sizer.GetChildren():
			self.sizer.Hide(object.GetWindow(), recursive=True)
		self.sizer.Clear()
		self.sizer.Add(child, 1, flag=wx.EXPAND)
		for object in self.sizer.GetChildren():
			self.sizer.Show(object.GetWindow(), recursive=True)
		
		self.sizer.Layout()
		self.Layout()
		print self.GetSize()
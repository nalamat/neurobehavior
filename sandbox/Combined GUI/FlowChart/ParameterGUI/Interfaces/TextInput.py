#
#  TextInput.py
#  GUI
#
#  Created by spencer3 on 6/11/10.
#  Copyright (c) 2010 __MyCompanyName__. All rights reserved.
#

class TextInput:
	def __init__(self, name, defaultValue, validationFunction):
		self.name = name
		self.defaultValue = defaultValue
		self.validator = validationFunction
		self.value = defaultValue
		self.panel=None
		self.GetValue = None
		
	def wxWidget(self, parent):
		import wx
		self.panel = wx.Panel(parent, wx.ID_ANY)
		title =wx.StaticText(self.panel, wx.ID_ANY, self.name)
		userInputValue = wx.TextCtrl(self.panel, wx.ID_ANY, value=str(self.value))
		sizer = wx.BoxSizer(wx.HORIZONTAL)
		sizer.Add(title, 1)
		sizer.Add(userInputValue, 1)
		self.panel.SetSizer(sizer)
		self.panel.Show()
		self.GetValue = userInputValue.GetValue
		return self.panel
		
if __name__ == '__main__':
	import wx
	app = wx.App(False)
	frame = wx.Frame(None, -1, "test")
	parameterSelectorText = wx.StaticText(frame,wx.ID_ANY, "Parameter:")
	parameterSelector = wx.ComboBox(frame, wx.ID_ANY, "", choices=["0","1","2"], size=(-1,50), style=wx.CB_READONLY)
	input = TextInput("foo", "", str)
	inputWidget = input.wxWidget(frame)
	gs = wx.GridBagSizer(hgap=5)
	gs.Add(parameterSelectorText, pos = (0,0), flag=wx.ALIGN_RIGHT)
	gs.Add(parameterSelector, pos = (0,1), flag=wx.ALIGN_LEFT)
	gs.Add(inputWidget, (1,0), span=(1, 2), flag=wx.EXPAND)
	frame.SetSizer(gs)
	frame.Show()
	input2 = TextInput("foo2", "foo2", str)
	input2Widget = input2.wxWidget(frame)
	gs.Detach(inputWidget)
	gs.Layout()

	gs.Add(input2Widget, (1,0), span=(1,2), flag=wx.EXPAND)
	gs.Layout()
	input2Widget.Show(False)
	input2Widget.Show(True)

	#frame.Show(show=False)
	#frame.Show(show=True)

	app.MainLoop()
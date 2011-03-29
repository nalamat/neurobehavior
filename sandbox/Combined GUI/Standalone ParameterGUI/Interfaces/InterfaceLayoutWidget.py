

import wx

class InterfaceLayoutWidget(wx.Panel):
	rSquareSidePixels=10
	EMPTY_CELL = 0
	FILLED_CELL = 1
	SELECTED_CELL = 2
	def __init__(self, parent, id, numCols, numRows, currentGridLayout = [], toCall = lambda x:None):
		wx.Panel.__init__(self, parent, id, size=(numRows*InterfaceLayoutWidget.rSquareSidePixels, numCols*InterfaceLayoutWidget.rSquareSidePixels))
		
		self.Bind(wx.EVT_LEFT_DOWN, self.startDragEvent)
		self.Bind(wx.EVT_MOTION, self.handleMouseMotion)
		self.Bind(wx.EVT_LEFT_UP, self.endDragEvent)
		self.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self.endMouseCapture)
		self.Bind(wx.EVT_PAINT, self.onPaint)
		
		self.beginDragPosition = (None, None)
		self.endDragPosition = (None, None)
		self.interfaceLayoutGrid = [None]*numRows
		for i in xrange(numRows):
			self.interfaceLayoutGrid[i] = [InterfaceLayoutWidget.EMPTY_CELL]*numCols
		#Fill in for alreadyExistingWidgets in Grid:
		for ul, ur, (colspan, rowspan) in currentGridLayout:
			for col in xrange(ul, ul+colspan, 1):
				for row in xrange(ur, ur+rowspan, 1):
					self.interfaceLayoutGrid[row][col] = InterfaceLayoutWidget.FILLED_CELL
		self.toCall = toCall
	
	def bindFunc(self, func):
		self.toCall = func
	
	def getSize(self):
		return InterfaceLayoutWidget.rSquareSidePixels*(1+len(self.interfaceLayoutGrid)), InterfaceLayoutWidget.rSquareSidePixels*(1+len(self.interfaceLayoutGrid[0]))
	
	def isCellSelected(self, col, row):
		xRange = col*InterfaceLayoutWidget.rSquareSidePixels, (col+1)*InterfaceLayoutWidget.rSquareSidePixels
		yRange = row*InterfaceLayoutWidget.rSquareSidePixels, (row+1)*InterfaceLayoutWidget.rSquareSidePixels
		selectedXRange = min((self.beginDragPosition[0], self.endDragPosition[0])), max((self.beginDragPosition[0], self.endDragPosition[0]))
		selectedYRange = min((self.beginDragPosition[1], self.endDragPosition[1])), max((self.beginDragPosition[1], self.endDragPosition[1]))
		if (selectedXRange[0] > xRange[0] and selectedXRange[0] < xRange[1]) or (selectedXRange[1] >= xRange[0] and selectedXRange[1] < xRange[1]) or (xRange[0] >= selectedXRange[0] and xRange[0] <= selectedXRange[1]):
			if (selectedYRange[0] > yRange[0] and selectedYRange[0] < yRange[1]) or (selectedYRange[1] >= yRange[0] and selectedYRange[1] < yRange[1]) or (yRange[0] >= selectedYRange[0] and yRange[0] <= selectedYRange[1]):
				return True
		return False
		
	def onPaint(self, event):
		width, height = self.GetSize()
		dc = wx.PaintDC(self)
		dc.SetPen(wx.Pen('Black'))
		
		for rowNum in xrange(len(self.interfaceLayoutGrid)):
			for colNum in xrange(len(self.interfaceLayoutGrid[rowNum])):
				cellType = self.interfaceLayoutGrid[rowNum][colNum]
				#if cellType == InterfaceLayoutWidget.FILLED_CELL: print rowNum, colNum, cellType
				fillColor = "White"
				if self.isCellSelected(row=rowNum, col=colNum):
					cellType += InterfaceLayoutWidget.SELECTED_CELL
				if cellType == InterfaceLayoutWidget.FILLED_CELL:
					fillColor = "Blue"
				elif cellType == InterfaceLayoutWidget.SELECTED_CELL:
					fillColor = "Red"
				elif cellType > InterfaceLayoutWidget.SELECTED_CELL:
					fillColor = "Purple"
				dc.SetBrush(wx.Brush(fillColor))
				dc.DrawRectangle(colNum*InterfaceLayoutWidget.rSquareSidePixels, rowNum*InterfaceLayoutWidget.rSquareSidePixels, InterfaceLayoutWidget.rSquareSidePixels, InterfaceLayoutWidget.rSquareSidePixels)
				
	def startDragEvent(self, event):
		#print "Oh Hey!"
		self.CaptureMouse()
		self.beginDragPosition = event.GetPosition()
		self.endDragPosition = event.GetPosition()
		self.Refresh()
		
	def endDragEvent(self, event):
		self.endMouseCapture(event)
		self.toCall()
		
	def endMouseCapture(self, event):
		if self.HasCapture():
			self.ReleaseMouse()
	
	def getSelectedRange(self):
		firstCell = None
		lastCell = None
		for row in xrange(len(self.interfaceLayoutGrid)):
			for col in xrange(len(self.interfaceLayoutGrid[row])):
				#print col, row, self.interfaceLayoutGrid[row][col]
				if self.isCellSelected(col, row):
					if firstCell == None: firstCell = (col, row)
					lastCell = (col, row)
		return firstCell[0], firstCell[1], (lastCell[0] - firstCell[0] + 1, lastCell[1] - firstCell[1]+1)
		
	def handleMouseMotion(self, event):
		if event.Dragging() and event.LeftIsDown():
			self.endDragPosition = event.GetPosition()
			self.Refresh()
	
if __name__=='__main__':
	app = wx.App(False)
	window = wx.Frame(None, -1, "Pracitice Window")
	layoutInterface= InterfaceLayoutWidget(window, -1, 5, 5)
	window.Show()
	app.MainLoop()
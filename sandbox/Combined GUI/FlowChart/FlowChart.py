import wx
import cPickle, os
from SignalParameter import SignalParameter
import FlowChartItems
import FlowChartItems.SignalGenerators

class FlowChart(wx.Panel):
	def __init__(self, parent, id, title="Flow chart", guiPanel=None):
		wx.Panel.__init__(self, parent, id)
		
		self.__numItems = 0
		self.flowChartItems = {} #Just a hash of itemID -> flowChartItem
		
		self.monoSpeakerButton = wx.ToggleButton(self, wx.ID_ANY, label="1")
		self.stereoSpeakerButton = wx.ToggleButton(self, wx.ID_ANY, label="2")
		self.runButton = wx.ToggleButton(self, wx.ID_ANY,label="Run")
		self.stopButton = wx.ToggleButton(self, wx.ID_ANY, label="Stop!")
		self.saveButton = wx.Button(self, wx.ID_ANY, label="Save")
		self.loadButton = wx.Button(self, wx.ID_ANY, label="Load")
		self.monoSpeakerButton.Bind(wx.EVT_TOGGLEBUTTON, self.toggleMono)
		self.stereoSpeakerButton.Bind(wx.EVT_TOGGLEBUTTON, self.toggleStereo)
		self.runButton.Bind(wx.EVT_TOGGLEBUTTON, self.runExperiment)
		self.stopButton.Bind(wx.EVT_TOGGLEBUTTON, self.stopExperiment)
		self.saveButton.Bind(wx.EVT_BUTTON, self.save)
		self.loadButton.Bind(wx.EVT_BUTTON, self.load)
		self.sizer = wx.BoxSizer()
		self.sizer.Add(self.monoSpeakerButton)
		self.sizer.Add(self.stereoSpeakerButton)
		self.sizer.Add(self.runButton)
		self.sizer.Add(self.stopButton)
		self.sizer.Add(self.saveButton)
		self.sizer.Add(self.loadButton)
		self.sizer.Layout()
		self.SetSizer(self.sizer)
		
		self.menu = wx.Menu()
		self.createModuleMenu('FlowChartItems', self.menu, menuName = "Add")
		self.lastRightClick = None #Keeps track of the position where the user has right-clicked the mouse
		
		self.__leftButtonDown = False
		self.__shiftDown = False
		self.__lastMousePosition = (None, None)
		self.__itemSelected = None
		self.__attachmentLineSegments = {}
		self.__parameterToAttach = None
		self.__itemsAttached = {} #Hash table of item -> (item attached to one of its parameters, parameter Attached)
		self.Bind(wx.EVT_MOTION, self.handleMouseMotion)
		self.Bind(wx.EVT_LEFT_DOWN, self.handleLeftClickBegin)
		self.Bind(wx.EVT_LEFT_UP, self.handleLeftClickEnd)
		self.Bind(wx.EVT_RIGHT_DOWN, self.rightButtonMenu)
		self.Bind(wx.EVT_PAINT, self.onPaint)
		self.guiPanel = guiPanel
	
	def save(self, event):
		dialog = wx.FileDialog(self, "Save As...", defaultDir = "FlowCharts", style=wx.FD_SAVE)
		if dialog.ShowModal() == wx.ID_OK:
			toPickle = self.saveState()
			outputFile = dialog.GetFilename()
			if '.' not in outputFile: outputFile += '.data'
			outputDirectory = dialog.GetDirectory()
			cPickle.dump(toPickle, open(os.path.join(outputDirectory, outputFile), 'w'))
	
	def load(self, event):
		dialog = wx.FileDialog(self, "Load FlowChart", defaultDir = "FlowCharts", style=wx.FD_OPEN)
		if dialog.ShowModal() == wx.ID_OK:
			fName = dialog.GetPath()
			toLoad = cPickle.load(open(fName, 'r'))
			self.loadState(toLoad)
	
	def clear(self):
		for item in self.flowChartItems.values():
			item.Destroy()
		self.flowChartItems = {}
		self.__attachmentLineSegments = {}
		self.__itemsAttached = {}
	def saveState(self):
		saveHash={}
		saveHash["attachmentLineSegments"] = {}
		for item, attachedLineSegments in self.__attachmentLineSegments.iteritems():
			saveHash["attachmentLineSegments"][item.GetId()] = attachedLineSegments
		saveHash["flowChartItems"] = {}
		for key, item in self.flowChartItems.iteritems():
			saveHash["flowChartItems"][key] = {"pos": item.GetPosition(), "id": key, "itemName": item.classHierarchy}
		saveHash["itemsAttached"] = {}
		for item, attachmentList in self.__itemsAttached.iteritems():
			saveHash["itemsAttached"][item.GetId()] = [(attachItem.GetId(), param.name) for attachItem, param in attachmentList]
		return saveHash
	
	def loadState(self, loadHash):
		self.clear()
		for key, flowChartItem in loadHash["flowChartItems"].iteritems():
			pos = flowChartItem["pos"]
			itemName = flowChartItem["itemName"]
			id = flowChartItem["id"]
			self.createFlowChartItem(itemName, pos, id)
		
		self.__attachmentLineSegments = {}
		for itemID, attachedLineSegments in loadHash["attachmentLineSegments"].iteritems():
			self.__attachmentLineSegments[self.flowChartItems[itemID]] = attachedLineSegments
			
		for keyID, attachmentList in loadHash["itemsAttached"].iteritems():
			self.itemsAttached = {}
			itemBeingAttached = self.flowChartItems[keyID]
			paramNameToParam = {}
			for param in itemBeingAttached.parameters:
				paramNameToParam[param.name] = param
			for param in itemBeingAttached.waveInputs:
				paramNameToParam[param.name] = param
			attachList = []
			for attachingItemID, paramName in attachmentList:
				attachingItem = self.flowChartItems[attachingItemID]
				self.attachParameter(attachingItem, itemBeingAttached, paramNameToParam[paramName])
				attachList.append((attachingItem, paramNameToParam[paramName]))
			self.itemsAttached[itemBeingAttached] = attachList
		self.Refresh()
			
	def toggleMono(self, event):
		self.monoSpeakerButton.SetValue(True)
		self.stereoSpeakerButton.SetValue(False)
		for itemID, flowChartItem in self.flowChartItems.iteritems():
			flowChartItem.setStereo(False)
		
	def toggleStereo(self, event):
		self.stereoSpeakerButton.SetValue(True)
		self.monoSpeakerButton.SetValue(False)
		for itemID, flowChartItem in self.flowChartItems.iteritems():
			flowChartItem.setStereo(True)
			
	def runExperiment(self, event):
		print "attachmentLineSegments Events:",self.__attachmentLineSegments.keys()
		print "Attached Items:", self.__itemsAttached
		self.runButton.SetValue(True)
		self.stopButton.SetValue(False)
		for itemID, flowChartItem in self.flowChartItems.iteritems():
			flowChartItem.runExperiment()
		
	def stopExperiment(self, event):
		self.runButton.SetValue(False)
		self.stopButton.SetValue(True)
		for itemID, flowChartItem in self.flowChartItems.iteritems():
			flowChartItem.stopExperiment()

	def onPaint(self, event):
		dc = wx.PaintDC(self)
		for item, lineSegments in self.__attachmentLineSegments.iteritems():
			self.drawLineSegments(lineSegments)
		return
		
	def handleParameterDetach(self, itemToDetach):
		if itemToDetach in self.__attachmentLineSegments:
			self.drawLineSegments(self.__attachmentLineSegments[self.__itemSelected], dcLogicalFunction=wx.XOR)
			del self.__attachmentLineSegments[itemToDetach]
		for itemID, attachmentList in self.__itemsAttached.iteritems():
			indicesToDelete = []
			for i in xrange(len(attachmentList)-1,-1,-1):
				if attachmentList[i][0] == itemToDetach: indicesToDelete.append(i)
			for index in indicesToDelete:
				del attachmentList[index]
		
	def handleLeftClickBegin(self, event):
		x, y = event.GetPositionTuple()
		self.__leftButtonDown = True
		self.__shiftDown = event.ShiftDown()
		eventID = event.GetId()
		if eventID in self.flowChartItems:
			for flowChartItem in self.flowChartItems.values():
				flowChartItem.loseFocus()
			self.__itemSelected = self.flowChartItems[eventID]
			self.__itemSelected.gainFocus()
			if self.__shiftDown: 
				self.__itemSelected.detachParameter()
				self.handleParameterDetach(self.__itemSelected)
				
			panelPosition = self.__itemSelected.GetPositionTuple()
			self.__lastMousePosition = (x+panelPosition[0], y+panelPosition[1])
		else:
			self.__lastMousePosition = (x,y)
		
	def moveFlowChartItem(self, event):
		eventID = event.GetId()
		newPosition = event.GetPositionTuple()
		if eventID in self.flowChartItems:
			panelPosition = self.flowChartItems[eventID].GetPositionTuple()
			newPosition = (newPosition[0] + panelPosition[0], newPosition[1]+panelPosition[1])
		dx = newPosition[0] - self.__lastMousePosition[0]
		dy = newPosition[1] - self.__lastMousePosition[1]
		currentPanelPosition = self.__itemSelected.GetPositionTuple()
		newPanelPosition = (currentPanelPosition[0] + dx, currentPanelPosition[1] + dy)
		self.__itemSelected.Move(newPanelPosition)
		if self.__itemSelected in self.__attachmentLineSegments:
			#Then we need to redo the lines!
			self.drawLineSegments(self.__attachmentLineSegments[self.__itemSelected], dcLogicalFunction=wx.XOR)
			#Then we need to change the origin point
			beginPoint = self.__attachmentLineSegments[self.__itemSelected][0][0]
			endPoint = self.__attachmentLineSegments[self.__itemSelected][-1][-1]
			beginPoint = (beginPoint[0]+dx, beginPoint[1]+dy)
			self.__attachmentLineSegments[self.__itemSelected] = self.createFlowLines(beginPoint, endPoint)
			#self.drawLineSegments(self.__attachmentLineSegments[self.__itemSelected])
		if self.__itemSelected in self.__itemsAttached:
			attachingItems = set((item[0] for item in self.__itemsAttached[self.__itemSelected]))
			for item in attachingItems:
				#So first erase the line!
				self.drawLineSegments(self.__attachmentLineSegments[item], dcLogicalFunction=wx.XOR)
				#We need to move the end point of all these attachment Line Segments now
				beginPoint = self.__attachmentLineSegments[item][0][0] 
				endPoint = self.__attachmentLineSegments[item][-1][-1] 
				endPoint = (endPoint[0] + dx, endPoint[1]+dy)
				#print beginPoint, endPoint
				self.__attachmentLineSegments[item] = self.createFlowLines(beginPoint, endPoint)
		self.Refresh()
				
		self.__lastMousePosition = newPosition

	def drawParameterAttachmentLine(self, event):
		eventID = event.GetId()
		if self.flowChartItems.get(eventID, -1) == self.__itemSelected:
			return #Then we don't need to draw anything!
		if self.__itemSelected in self.__attachmentLineSegments:
			self.drawLineSegments(self.__attachmentLineSegments[self.__itemSelected],dcLogicalFunction=wx.XOR)
		itemPosition = self.__itemSelected.GetPositionTuple()
		itemSpan = self.__itemSelected.GetSize()
		beginPoint = (itemPosition[0]+itemSpan[0], itemPosition[1] + itemSpan[1]/2)
			
		if eventID not in self.flowChartItems:
			#Here we need to draw new arrow line segments!
			endPoint = event.GetPositionTuple()
		else:
			#Now we need to try and deal with actually attaching this sucker!
			toAttachItemPosition = self.flowChartItems[eventID].GetPositionTuple()
			self.__itemToAttach = self.flowChartItems[eventID]
			self.__parameterToAttach, attachmentXCoord, attachmentYCoord = self.__itemToAttach.getClosestParameterToMouseEvent(event)
			if self.__parameterToAttach != None: #Then there is a potential parameter to attach to
				endPoint = (attachmentXCoord+toAttachItemPosition[0], attachmentYCoord+toAttachItemPosition[1])
		self.__attachmentLineSegments[self.__itemSelected] = self.createFlowLines(bp = beginPoint, ep = endPoint)
		self.drawLineSegments(self.__attachmentLineSegments[self.__itemSelected], dcLogicalFunction=wx.XOR)
		self.Refresh()
		
	def createFlowLines(self, bp, ep):
		lineSegmentsToReturn = []
		lineSegmentsToReturn.append((bp, ((bp[0]+ep[0])/2, bp[1])))
		lineSegmentsToReturn.append((((bp[0]+ep[0])/2,bp[1]), ((bp[0]+ep[0])/2, ep[1])))
		lineSegmentsToReturn.append((((bp[0]+ep[0])/2, ep[1]), ep))
		return lineSegmentsToReturn

	def drawLineSegments(self, lineSegments, dcPenColor="Black", dcLogicalFunction=wx.COPY):
		#print "Drawing lineSegments",lineSegments
		dc = wx.ClientDC(self)
		dc.BeginDrawing()
		
		dc.SetLogicalFunction(dcLogicalFunction)
		dc.SetPen(wx.Pen(dcPenColor))
		
		for (bp, ep) in lineSegments:
			dc.DrawLine(bp[0], bp[1], ep[0],ep[1])
		
	def handleMouseMotion(self, event):
		if self.__leftButtonDown:
			if self.__itemSelected != None:
				if self.__shiftDown:
					self.drawParameterAttachmentLine(event)
				else:
					self.moveFlowChartItem(event)
				
	def attachParameter(self, attachingItem, itemBeingAttached, parameterBeingAttached):
		attachingItem.attachParameter(parameterBeingAttached)
		if itemBeingAttached in self.__itemsAttached:
			self.__itemsAttached[itemBeingAttached].append((attachingItem, parameterBeingAttached))
		else:
			self.__itemsAttached[itemBeingAttached] = [(attachingItem, parameterBeingAttached)]

	def handleLeftClickEnd(self, event):
		if self.__leftButtonDown and self.__shiftDown and self.__itemSelected != None:
			if self.__parameterToAttach != None:
				self.attachParameter(attachingItem = self.__itemSelected, itemBeingAttached=self.__itemToAttach, parameterBeingAttached = self.__parameterToAttach)
			else: #Need to erase the line segments already drawn!
				self.drawLineSegments(self.__attachmentLineSegments[self.__itemSelected], dcLogicalFunction=wx.XOR)
				self.Refresh()
				del self.__attachmentLineSegments[self.__itemSelected]
				
		self.__leftButtonDown = False
		self.__shiftDown = False
		self.__itemSelected = None
		self.__parameterToAttach = None
		

	def createFlowChartItem(self, itemName, pos, id=None):
		if pos == "mouse":
			pos = self.lastRightClick
		if id == None or id == -1: id = wx.NewId()
		creationString = "item = %s.%s(self, id, pos, self.guiPanel)" %(itemName, itemName.split('.')[-1])
		exec(creationString)
		item.classHierarchy = itemName
		self.flowChartItems[id] = item
		self.__numItems += 1
		self.Show(False)
		self.Show(True)
		print self.__numItems-1

		
	def createModuleMenu(self, moduleName, menu, menuName=None):
		print "Trying to Add", moduleName
		try:
			exec("import %s" % (moduleName)) 
		except Exception, e:
			print "Error importing",moduleName,str(e)
			return
		try:
			exec("all = getattr(%s, '__all__')" %(moduleName))
		except AttributeError:
			#Then this is a module (and not a folder)
			menuID = wx.NewId()
			menuItem = wx.MenuItem(menu, menuID, moduleName.split('.')[-1])
			#print "Adding",moduleName
			def bindToMenuItem(event, self=self, itemName = moduleName, pos = "mouse"):
				self.createFlowChartItem(itemName, pos)
			self.Bind(wx.EVT_MENU, bindToMenuItem, id=menuID)
			menu.AppendItem(menuItem)
			return
		#Now we need to make a submenu
		#print "Creating Submenu",moduleName
		subMenu = wx.Menu()
		for module in all:
			self.createModuleMenu(moduleName+'.'+module, subMenu)
		if menuName == None:
			menuName = moduleName.split('.')[-1]
		menu.AppendMenu(wx.ID_ANY, menuName, subMenu)
		
	def rightButtonMenu(self, event):
		self.lastRightClick = event.GetPosition()
		self.PopupMenu(self.menu)
		
from Interfaces import AxisWidget
from Interfaces import GraphWidget

def load(parent, id, widgetAttrDict, soundManager):
	className = widgetAttrDict["WidgetClassName"]
	exec("widget = %s.%s(parent, id, '', soundManager=soundManager)" %(className, className))
	widget.loadState(widgetAttrDict)
	return widget
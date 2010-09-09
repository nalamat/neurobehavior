from cns.channel import BufferedMultiChannel, MultiChannel
from cns.widgets.views.decimated_plot import DecimatedChannelPlot, \
    ChannelDataSource
from cns.widgets.views.channel_view import NewMultiChannelView
from enthought.chaco.api import VPlotContainer, LinearMapper, DataRange1D, PlotAxis
from enthought.chaco.tools.api import ZoomTool, PanTool
from enthought.enable.api import ComponentEditor
from enthought.pyface.timer.api import Timer
from enthought.traits.api import HasTraits, Instance
from enthought.traits.ui.api import View, Item
import numpy as np

class Foo(HasTraits):

    component = Instance(NewMultiChannelView)
    timer = Instance(Timer)
    n = 25e3
    ch = 16
    mc = Instance(MultiChannel)

    def __init__(self, *args, **kw):
        HasTraits.__init__(self, *args, **kw)
        self.timer = Timer(1, self.tick)

    def tick(self):
        y = np.random.normal(0, 5, self.n*self.ch).reshape((-1, self.ch))
        self.mc.send(y)

    def _component_default(self):
        self.mc = BufferedMultiChannel(window=10, fs=1e3, channels=self.ch)
        component = NewMultiChannelView(channel=self.mc)
        return component

    traits_view = View('component{}@',
                       height=600,
                       width=600,
                       resizable=True)

Foo().configure_traits()

from os.path import join
import numpy as np
from cns.chaco.snippet_channel_plot import SnippetChannelPlot

from enthought.enable.api import Component, ComponentEditor, Window
from enthought.traits.api import HasTraits, Instance, Button, Any
from enthought.traits.ui.api import Item, Group, View, Controller
from enthought.pyface.timer.api import Timer
from enthought.chaco.api import (LinearMapper, DataRange1D,
        OverlayPlotContainer, PlotAxis)

from tdt import DSPCircuit
from cns import RCX_ROOT
from cns.chaco.helpers import add_default_grids
from cns.chaco.tools.window_tool import WindowTool
from cns.channel import FileSnippetChannel
from cns.data.h5_utils import get_temp_file

class Demo(HasTraits):

    traits_view = View(
            Item('handler.button'),
            Item('handler.container', editor=ComponentEditor(size=(400,400))),
            resizable=True)

class DemoController(Controller):

    iface = Any
    timer = Any
    snippet_source = Any
    snippet_store = Any
    plot = Any
    container = Any
    button = Button
    tool = Any

    def _button_fired(self):
        hoops = self.tool.get_hoops()
        coeffs = np.zeros((32, 3))
        for i, hoop in enumerate(hoops):
            x = round(hoop[0]*self.snippet_source.fs)
            coeffs[x] = hoop[1], hoop[2], i+1
            print x, hoop[1], hoop[2], i+1
        self.iface.set_coefficients('spike1_c', coeffs.ravel())
        self.plot.last_reset = len(self.snippet_store.buffer)

    def _container_default(self):
        container = OverlayPlotContainer(padding=[50, 50, 50, 50])
        index_mapper = LinearMapper(range=DataRange1D(low=0, high=0.0005))
        value_mapper = LinearMapper(range=DataRange1D(low=-0.00025, high=0.0005))
        plot = SnippetChannelPlot(history=100, channel=self.snippet_store,
                value_mapper=value_mapper, index_mapper=index_mapper)
        self.plot = plot
        axis = PlotAxis(orientation='left', component=plot)
        plot.overlays.append(axis)
        axis = PlotAxis(orientation='bottom', component=plot)
        plot.overlays.append(axis)
        self.tool = WindowTool(component=plot)
        plot.overlays.append(self.tool)
        container.add(plot)

#        plot = SnippetChannelPlot(history=100, channel=self.snippet_store,
#                value_mapper=value_mapper, index_mapper=index_mapper,
#                classifier=1, line_color='red')
#        container.add(plot)
#
        #plot = SnippetChannelPlot(history=100, channel=self.snippet_store,
        #        value_mapper=value_mapper, index_mapper=index_mapper,
        #        classifier=2, line_color='green')
        #container.add(plot)

        #plot = SnippetChannelPlot(history=5, channel=self.snippet_store,
        #        value_mapper=value_mapper, index_mapper=index_mapper,
        #        classifier=2, line_color='blue')
        #container.add(plot)

        return container

    def _snippet_store_default(self):
        datafile = get_temp_file()
        return FileSnippetChannel(node=datafile.root, name='snippet',
                snippet_size=30)

    def init(self, info):
        filename = join(RCX_ROOT, 'physiology')
        self.iface = DSPCircuit(filename, 'RZ5')
        self.iface.set_tag('spike1_a', 1e-4)
        self.snippet_source = self.iface.get_buffer('spike1', 'r',
                block_size=32)
        self.snippet_store.fs = self.snippet_source.fs
        self.iface.start()
        self.iface.trigger('A', 'high')
        self.timer = Timer(100, self.monitor)

    def monitor(self):
        data = self.snippet_source.read().reshape((-1, 32))
        self.snippet_store.send(data[:,1:-1], data[:,0].view('int32'),
                data[:,-1].view('int32'))

Demo().configure_traits(handler=DemoController())

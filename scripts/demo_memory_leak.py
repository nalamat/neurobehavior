import os
os.environ['ETS_TOOLKIT'] = 'wx' 
#os.environ['QT_API'] = 'pyqt'

import time
import numpy as np
import tables
from traits.api import Instance, HasTraits
from traitsui.api import Controller, Item, View
from pyface.timer.api import Timer
from enable.api import ComponentEditor
from chaco.api import LinearMapper, DataRange1D, OverlayPlotContainer
from cns.channel import FileChannel
from cns.chaco_exts.channel_plot import ChannelPlot
from cns.chaco_exts.ttl_plot import TTLPlot
from cns.chaco_exts.channel_data_range import ChannelDataRange
#import objgraph

class PlotController(Controller):

    timer = Instance(Timer)

    def init(self, info):
        self.timer = Timer(100, self.monitor_experiment, info)
        #objgraph.show_growth()

    def monitor_experiment(self, info):
        data = np.random.randint(2) * np.ones(50)
        info.object.ttl_channel.send(data)
        data = np.random.randint(5, size=2)
        info.object.channel.send(data)

class PlotExperiment(HasTraits):

    node = Instance('tables.Group')
    ttl_channel = Instance('cns.channel.Channel')
    channel = Instance('cns.channel.Channel')
    plot = Instance('enable.component.Component')

    def _ttl_channel_default(self):
        return FileChannel(node=self.node, name='ttl_channel', fs=500,
                           dtype=np.bool)

    def _channel_default(self):
        return FileChannel(node=self.node, name='channel', fs=20,
                           dtype=np.int32)

    def _plot_default(self):
        container = OverlayPlotContainer(padding=[50, 20, 20, 50])
        range = ChannelDataRange(sources=[self.channel], span=10, trig_delay=0)
        index_mapper = LinearMapper(range=range)
        value_mapper = LinearMapper(range=DataRange1D(low=-1, high=5))
        plot = ChannelPlot(channel=self.channel, 
                       index_mapper=index_mapper,
                       value_mapper=value_mapper,
                       line_width=3,
                        )
        container.add(plot)
        value_mapper = LinearMapper(range=DataRange1D(low=0, high=1))
        plot = TTLPlot(channel=self.ttl_channel, 
                       index_mapper=index_mapper,
                       value_mapper=value_mapper,
                       fill_color=(1, 0, 0, 0.5))
        container.add(plot)
        return container

    traits_view = View(
        Item('plot', editor=ComponentEditor(height=600, width=600),
             show_label=False, height=600, width=600),
        resizable=True)

if __name__ == '__main__':
    with tables.openFile('temp.hd5', 'w') as fh:
        PlotExperiment(node=fh.root).configure_traits(handler=PlotController())

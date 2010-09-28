from cns.channel import BufferedChannel
from cns.widgets.views.decimated_plot import DecimatedChannelPlot, \
    ChannelDataSource
from enthought.chaco.api import VPlotContainer, LinearMapper, DataRange1D, PlotLabel, PlotAxis
from enthought.chaco.tools.api import ZoomTool, PanTool
from enthought.enable.api import ComponentEditor
from enthought.pyface.timer.api import Timer
from enthought.traits.api import HasTraits, Instance
from enthought.traits.ui.api import View, Item
import numpy as np

class Foo(HasTraits):

    component = Instance(VPlotContainer)
    timer = Instance(Timer)
    n = 25e3

    def __init__(self, *args, **kw):
        HasTraits.__init__(self, *args, **kw)
        self.timer = Timer(1, self.tick)

    def tick(self):
        for plot in self.component.components:
            y = np.random.normal(0, 5, self.n)
            try:
                plot.channel_source.channel.send(y)
            except:
                pass

    def _component_default(self):
        component = VPlotContainer(
                resizable='hv',
                bgcolor='transparent',
                fill_padding=True,
                padding=10,
                spacing=25,
                stack_order='top_to_bottom')
 
        idx_range = DataRange1D(low_setting=-10, high_setting=0)
        val_range = DataRange1D(low_setting=-20, high_setting=20)
        idx_map = LinearMapper(range=idx_range)
        #val_map = LinearMapper(range=val_range)
        zoom = None

        for i in range(16):
            ch = BufferedChannel(window=10, fs=10e3)
            ch.send(np.random.normal(0, 5, self.n))
            #idx_map = LinearMapper(range=idx_range)
            val_map = LinearMapper(range=val_range)
            ch_ds = ChannelDataSource(channel=ch)

            plot = DecimatedChannelPlot(channel_source=ch_ds, 
                                        index_mapper=idx_map,
                                        value_mapper=val_map,
                                        padding_left=50)
            #label = PlotLabel('%d' % (i+1), overlay_position='left', component=plot)
            #plot.overlays.append(label)
            axis = PlotAxis(orientation='left', component=plot,
                            small_haxis_style=True, title='Ch %d' % (i+1))
            plot.overlays.append(axis)
            
            if zoom is None:
                zoom = ZoomTool(component=plot, tool_mode="range", axis="index")
            plot.overlays.append(zoom)
            #plot.tools.append(PanTool(plot, constrain=True, constrain_key=None,
            #                          constrain_direction="x"))
            component.add(plot)
            
        axis = PlotAxis(orientation='bottom', mapper=idx_map, 
                        title='Post Trigger Time (s)')
        component.add(axis)
        return component

    traits_view = View(Item('component', editor=ComponentEditor()),
                       height=600,
                       width=600,
                       resizable=True)

Foo().configure_traits()

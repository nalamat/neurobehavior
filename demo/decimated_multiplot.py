from enthought.traits.api import HasTraits, Instance, Int
from enthought.traits.ui.api import View, Item
from enthought.enable.api import Component, ComponentEditor
from enthought.chaco.api import Plot, ArrayPlotData, VPlotContainer, \
    ArrayDataSource, LinearMapper, DataRange1D
from enthought.chaco.tools.api import ZoomTool, PanTool
import numpy as np 

from cns.widgets.views.decimated_plot import DecimatedMultiPlot, \
    create_decimated_plot, ArrayDataSource2D

from enthought.pyface.timer.api import Timer
import time

class Foo(HasTraits):

    component = Instance(VPlotContainer)
    timer = Instance(Timer)
    counter = 0

    def __init__(self, *args, **kw):
        HasTraits.__init__(self, *args, **kw)
        self.timer = Timer(1, self.tick)
        self.time = time.time()

    def tick(self):
        self.counter += 1
        if self.counter == 100:
            print 'Total time was', time.time()-self.time
        for plot in self.component.components:
            n = 100e3
            #ch = np.random.randint(1, 16)
            ch = 16
            #x = np.arange(n)
            y = np.random.normal(0, ch, n*ch).reshape((-1,ch))
            #plot.index.set_data(x)
            plot.value.set_data(y)

    def _component_default(self):
        component = VPlotContainer(
                resizable='hv',
                bgcolor='lightgray',
                fill_padding=True,
                padding=10,
                spacing=0,
                stack_order='top_to_bottom')
 
        idx_range = DataRange1D()
        val_range = DataRange1D()
        #idx_map = LinearMapper(range=idx_range)
        #val_map = LinearMapper(range=val_range)

        for i in range(1):
            n = 100e3
            x = ArrayDataSource(np.arange(n))
            y = ArrayDataSource2D(np.random.normal(0, 16, n*16).reshape((-1,16)))

            idx_range.add(x)
            val_range.add(y)

            idx_map = LinearMapper(range=idx_range)
            val_map = LinearMapper(range=val_range)

            plot = DecimatedMultiPlot(index=x, value=y, index_mapper=idx_map,
                    value_mapper=val_map)

            #plot = create_decimated_plot(x, y)
            zoom = ZoomTool(component=plot, tool_mode="box")
            plot.overlays.append(zoom)
            plot.tools.append(PanTool(plot))
            component.add(plot)

        return component

    traits_view = View(Item('component', editor=ComponentEditor()),
                       height=400,
                       width=400,
                       resizable=True)

Foo().configure_traits()

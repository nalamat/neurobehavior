from enthought.etsconfig.api import ETSConfig
ETSConfig.toolkit = 'qt4'
from enthought.traits.api import HasTraits, Instance, Int
from enthought.traits.ui.api import View, Item
from enthought.enable.api import Component, ComponentEditor
from enthought.chaco.api import Plot, ArrayPlotData, VPlotContainer, \
    ArrayDataSource, LinearMapper, DataRange1D
from enthought.chaco.tools.api import ZoomTool, PanTool
import numpy as np 

from cns.widgets.views.decimated_plot import DecimatedPlot, \
    create_decimated_plot, FastDataSource

from enthought.pyface.timer.api import Timer
import time

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

        for i in range(8):
            x = FastDataSource(np.arange(self.n))
            y = FastDataSource(np.random.normal(0, 5, self.n))

            idx_range.add(x)
            val_range.add(y)

            idx_map = LinearMapper(range=idx_range)
            val_map = LinearMapper(range=val_range)

            plot = DecimatedPlot(index=x, value=y, index_mapper=idx_map,
                    value_mapper=val_map)

            #plot = create_decimated_plot(x, y)
            zoom = ZoomTool(component=plot, tool_mode="range", axis="index")
            plot.overlays.append(zoom)
            plot.tools.append(PanTool(plot, constrain=True, constrain_key=None,
                                      constrain_direction="x", restrict_to_data=True))
            component.add(plot)

        return component

    traits_view = View(Item('component', editor=ComponentEditor()),
                       height=600,
                       width=600,
                       resizable=True)

Foo().configure_traits()

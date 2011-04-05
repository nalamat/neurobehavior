from cns.channel import Channel
from cns.chaco.ttl_plot import TTLPlot

from enthought.traits.api import Instance, HasTraits
from enthought.traits.ui.api import Controller, View, Item
from enthought.enable.api import ComponentEditor
from enthought.chaco.api import DataRange1D, LinearMapper, PlotLabel, \
        VPlotContainer, PlotAxis, PlotGrid, add_default_grids

class PlotContainer(HasTraits):

    plot = Instance(VPlotContainer)
    channel = Instance(Channel, ())

    def _plot_default(self):
        index_range = DataRange1D(low_setting=-10, high_setting=0)
        index_mapper = LinearMapper(range=index_range)

        container = VPlotContainer(resizable='hv', bgcolor='white',
                fill_padding=True, padding=50, spacing=50,
                stack_order='top_to_bottom')

        value_range = DataRange1D(low_setting=-0, high_setting=1)
        value_mapper = LinearMapper(range=value_range)
        plot = TTLPlot(channel=self.channel,
                index_mapper=index_mapper, value_mapper=value_mapper,
                color='black', line_width=4)
        axis = PlotAxis(component=plot, title="Time (s)",
                        orientation="top", ticks_visible=True)
        plot.overlays.append(axis)
        axis = PlotAxis(component=plot, title="Spout Contact (TTL)",
                        orientation="left", tick_visible=False)
        plot.overlays.append(axis)
        grid = PlotGrid(mapper=plot.index_mapper, component=plot,
                orientation='vertical', line_color='lightgray',
                line_style='dot', grid_interval=0.25)
        plot.underlays.append(grid)
        grid = PlotGrid(mapper=plot.index_mapper, component=plot,
                orientation='vertical', line_color='lightgray',
                line_style='solid', grid_interval=1)
        plot.underlays.append(grid)
        #axis = PlotAxis(orientation='left', component=plot,
        #        small_haxis_style=True, title='TTL')
        #plot.overlays.append(axis)
        container.add(plot)
        return container

    traits_view = View(Item('plot', editor=ComponentEditor(), show_label=False,
        width=600, height=600))

PlotContainer().configure_traits()

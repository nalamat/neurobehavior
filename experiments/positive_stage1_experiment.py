from enthought.traits.api import Instance, Any, DelegatesTo
from enthought.traits.ui.api import View, HGroup, HSplit, VGroup, Item

from enthought.enable.api import Component, ComponentEditor
from enthought.chaco.api import DataRange1D, LinearMapper, \
        PlotAxis, PlotGrid, OverlayPlotContainer

from cns.chaco.channel_data_range import ChannelDataRange
from cns.chaco.ttl_plot import TTLPlot

from abstract_experiment import AbstractExperiment
from positive_stage1_paradigm import PositiveStage1Paradigm
from positive_stage1_controller import PositiveStage1Controller
from positive_stage1_data import PositiveStage1Data

class PositiveStage1Experiment(AbstractExperiment):

    data        = Instance(PositiveStage1Data)
    paradigm    = Instance(PositiveStage1Paradigm, ())

    contact_plot = Any
    contact_plot_index_range = Instance(ChannelDataRange, ())
    contact_plot_range = DelegatesTo('contact_plot_index_range', 'range')
    contact_plot_interval = DelegatesTo('contact_plot_index_range', 'interval')

    def _data_default(self):
        return PositiveStage1Data(store_node=self.store_node)

    def _data_changed(self):
        index_range = self.contact_plot_index_range
        index_range.add(self.data.spout_TTL)
        index_mapper = LinearMapper(range=index_range)
        value_range = DataRange1D(low_setting=-0, high_setting=1)
        value_mapper = LinearMapper(range=value_range)
        container = OverlayPlotContainer(bgcolor='white', fill_padding=True,
                padding=50, spacing=50)

        # SIGNAL
        plot = TTLPlot(channel=self.data.signal_TTL,
                index_mapper=index_mapper, value_mapper=value_mapper,
                fill_color=(0, 1, 0, 0.5), rect_height=0.2, rect_center=0.9)
        container.add(plot)

        # PUMP
        plot = TTLPlot(channel=self.data.pump_TTL,
                index_mapper=index_mapper, value_mapper=value_mapper,
                fill_color=(0, 0, 1, 0.5), rect_height=0.2, rect_center=0.7)
        container.add(plot)

        # SPOUT
        plot = TTLPlot(channel=self.data.spout_TTL, reference=0,
                index_mapper=index_mapper, value_mapper=value_mapper,
                fill_color=(1, 1, 1, 0.5), rect_height=0.2, rect_center=0.5)
        container.add(plot)

        # OVERRIDE
        plot = TTLPlot(channel=self.data.override_TTL, reference=0,
                index_mapper=index_mapper, value_mapper=value_mapper,
                fill_color=(1, 0, 0, 0.5), rect_height=0.2, rect_center=0.3)
        container.add(plot)

        # FREE RUN
        plot = TTLPlot(channel=self.data.free_run_TTL, reference=0,
                index_mapper=index_mapper, value_mapper=value_mapper,
                fill_color=(1, 0, 0, 0.5), rect_height=0.2, rect_center=0.1)
        container.add(plot)

        # Add the axes and grids
        grid = PlotGrid(mapper=plot.index_mapper, component=plot,
                orientation='vertical', line_color='lightgray',
                line_style='dot', grid_interval=0.25)
        plot.underlays.append(grid)
        grid = PlotGrid(mapper=plot.index_mapper, component=plot,
                orientation='vertical', line_color='lightgray',
                line_style='solid', grid_interval=1)
        plot.underlays.append(grid)
        axis = PlotAxis(component=plot, title="Time (s)",
                        orientation="top", ticks_visible=True)
        plot.underlays.append(axis)
        tick_formatter = lambda s: "{0}:{1:02}".format(*divmod(int(s), 60))
        axis = PlotAxis(component=plot, title="Time (min:sec)",
                tick_label_formatter=tick_formatter, orientation="bottom")
        plot.underlays.append(axis)

        self.contact_plot = container

    traits_view = View(
            HSplit(
                VGroup(
                    Item('handler.toolbar', style='custom'),
                    VGroup(
                        Item('handler.status'),
                        Item('handler.current_time_elapsed', label='Run time'),
                        style='readonly',
                        label='Experiment',
                        show_border=True
                        ),
                    VGroup(
                        Item('handler.pump_toolbar', style='custom',
                             show_label=False), 
                        Item('handler.current_volume_dispensed', 
                             label='Dispensed (mL)', style='readonly'),
                        Item('object.paradigm.pump_rate'),
                        Item('object.paradigm.pump_syringe'),
                        Item('object.paradigm.pump_syringe_diameter', 
                             label='Diameter (mm)', style='readonly'),
                        label='Pump Status',
                        show_border=True,
                        ),
                    Item('paradigm', style='custom'),
                    show_labels=False,
                    ),
                VGroup(
                    HGroup(
                        Item('contact_plot_range', label='Range'), 
                        Item('contact_plot_interval', label='Scroll interval'),
                        ),
                    Item('contact_plot', editor=ComponentEditor(),
                        show_label=False, width=600, height=600),
                    ),
                ),
            resizable=True,
            close_result=False,
            handler=PositiveStage1Controller)

from enthought.enable.api import Component, ComponentEditor
from enthought.chaco.api import (LinearMapper, DataRange1D,
        OverlayPlotContainer)
from enthought.traits.ui.api import VGroup, HGroup, Item, Include, View, \
        InstanceEditor, RangeEditor, HSplit
from enthought.traits.api import Instance, HasTraits, Float, DelegatesTo, \
        Bool, on_trait_change

from physiology_paradigm_mixin import PhysiologyParadigmMixin

from cns.chaco.helpers import add_default_grids, add_time_axis
from cns.chaco.channel_data_range import ChannelDataRange
from cns.chaco.timeseries_plot import TimeseriesPlot
from cns.chaco.extremes_channel_plot import ExtremesChannelPlot
from cns.chaco.ttl_plot import TTLPlot

class PhysiologyExperimentMixin(HasTraits):

    # Acquire physiology?
    spool_physiology        = Bool(False)
    physiology_settings     = Instance(PhysiologyParadigmMixin, ())

    physiology_container    = Instance(Component)
    physiology_plot         = Instance(Component)
    physiology_index_range  = Instance(ChannelDataRange)
    physiology_value_range  = Instance(DataRange1D, ())

    physiology_channel_span = Float(0.5e-3)

    @on_trait_change('physiology_plot.channel_visible, physiology_channel_span')
    def _physiology_value_range_update(self):
        span = self.physiology_channel_span
        visible = len(self.physiology_plot.channel_visible)
        self.physiology_value_range.high_setting = visible*span
        self.physiology_value_range.low_setting = 0
        self.physiology_plot.channel_offset = span/2.0
        self.physiology_plot.channel_spacing = span

    def _physiology_channel_span_changed(self):
        self._physiology_value_range_update()

    def _physiology_channel_span_changed(self):
        self._physiology_value_range_update()

    @on_trait_change('data')
    def _generate_physiology_plot(self):
        container = OverlayPlotContainer(padding=[20, 20, 50, 50])

        # Create the index range shared by all the plot components
        self.physiology_index_range = ChannelDataRange(span=5, trig_delay=1,
                timeseries=self.data.physiology_ts,
                sources=[self.data.physiology_processed])

        # Create the TTL plot
        index_mapper = LinearMapper(range=self.physiology_index_range)
        value_mapper = LinearMapper(range=DataRange1D(low=0, high=1))
        plot = TTLPlot(channel=self.data.physiology_sweep,
                index_mapper=index_mapper, value_mapper=value_mapper,
                reference=0, fill_color=(0.25, 0.41, 0.88, 0.1),
                line_color='transparent', rect_center=0.5, rect_height=1.0)
        add_default_grids(plot, major_index=1, minor_index=0.25)
        add_time_axis(plot)
        container.add(plot)

        # Create the neural plots
        index_mapper = LinearMapper(range=self.physiology_index_range)
        value_mapper = LinearMapper(range=self.physiology_value_range)
        plot = ExtremesChannelPlot(channel=self.data.physiology_processed, 
                index_mapper=index_mapper, value_mapper=value_mapper)
        container.add(plot)
        add_default_grids(plot, major_index=1, minor_index=0.25)
        add_time_axis(plot)
        self.physiology_plot = plot

        self.physiology_container = container
        self._physiology_value_range_update()

    physiology_settings_group = VGroup(
            Item('physiology_settings', style='custom',
                editor=InstanceEditor(view='physiology_view')),
            Include('physiology_view_settings_group'),
            show_border=True,
            show_labels=False,
            )

    physiology_view_settings_group = VGroup(
            Item('object.physiology_index_range.update_mode', 
                label='Trigger mode'),
            Item('object.physiology_index_range.span',
                label='X span',
                editor=RangeEditor(low=0.1, high=10.0)),
            Item('object.physiology_index_range.trig_delay',
                label='Trigger delay',
                editor=RangeEditor(low=0.0, high=5.0)),
            Item('physiology_channel_span', label='Y span',
                editor=RangeEditor(low=0, high=5e-3)),
            #Item('physiology_offset', label='Plot offset',
            #    editor=RangeEditor(low=0, high=5e-3)),
            #Item('physiology_spacing', label='Plot spacing',
            #    editor=RangeEditor(low=0, high=5e-3)),
            label='Plot Settings',
            show_border=True,
            )

    physiology_view = View(
            HSplit(
                Include('physiology_settings_group'),
                Item('physiology_container', 
                    editor=ComponentEditor(width=1500, height=800), 
                    resizable=True),
                show_labels=False,
                ),
            resizable=True)

import numpy as np
from enthought.enable.api import Component, ComponentEditor
from enthought.chaco.api import (LinearMapper, DataRange1D,
        OverlayPlotContainer)
from enthought.traits.ui.api import VGroup, HGroup, Item, Include, View, \
        InstanceEditor, RangeEditor, HSplit, Tabbed
from enthought.traits.api import Instance, HasTraits, Float, DelegatesTo, \
     Bool, on_trait_change, Int, on_trait_change, Any, Range, Event, Property,\
     Tuple, List
from enthought.traits.ui.editors import RangeEditor

from physiology_paradigm_mixin import PhysiologyParadigmMixin

from enthought.chaco.api import PlotAxis, VPlotContainer, PlotAxis
from enthought.chaco.tools.api import ZoomTool
from cns.chaco.tools.window_tool import WindowTool
from cns.chaco.helpers import add_default_grids, add_time_axis
from cns.chaco.channel_data_range import ChannelDataRange
from cns.chaco.timeseries_plot import TimeseriesPlot
from cns.chaco.extremes_channel_plot import ExtremesChannelPlot
from cns.chaco.ttl_plot import TTLPlot
from cns.chaco.channel_range_tool import MultiChannelRangeTool
from cns.chaco.channel_number_overlay import ChannelNumberOverlay
from cns.chaco.snippet_channel_plot import SnippetChannelPlot
from cns import get_config

from cns.chaco.spike_overlay import SpikeOverlay
from cns.chaco.threshold_overlay import ThresholdOverlay

CHANNELS = get_config('PHYSIOLOGY_CHANNELS')
VOLTAGE_SCALE = 1e3
scale_formatter = lambda x: "{:.2f}".format(x*VOLTAGE_SCALE)

def ptt(event_times, trig_times):
    return np.concatenate([event_times-tt for tt in trig_times])

class Histogram(HasTraits):
    
    channel = Range(1, CHANNELS, 1)
    spikes = Any
    timeseries = Any
    bin_size = Float(0.25)
    bin_lb = Float(-1)
    bin_ub = Float(5)
    
    bins = Property(depends_on='bin_+')
    
    def _get_bins(self):
        return np.arange(self.bin_lb, self.bin_ub, self.bin_size)
    
    def _get_counts(self):
        spikes = self.spikes[self.channel-1]
        et = spikes.timestamps/spikes.fs
        return np.histogram(ptt(spikes, et), bins=self.bins)[0]
    
    def _get_histogram(self):
        self.spikes.timestamps[:]

class SortWindow(HasTraits):

    settings    = Any
    channels    = Any
    channel     = Range(1, CHANNELS, 1)
    
    plot        = Instance(SnippetChannelPlot)
    threshold   = Property(Float, depends_on='channel')
    sign        = Property(Bool, depends_on='channel')
    windows     = Property(List(Tuple(Float, Float, Float)), depends_on='channel')
    tool        = Instance(WindowTool)
    
    def _get_sign(self):
        return self.settings[self.channel-1].spike_sign
    
    def _set_sign(self, value):
        self.settings[self.channel-1].spike_sign = value
    
    def _get_threshold(self):
        return self.settings[self.channel-1].spike_threshold*VOLTAGE_SCALE
    
    def _set_threshold(self, value):
        self.settings[self.channel-1].spike_threshold = value/VOLTAGE_SCALE
        
    def _get_windows(self):
        if self.settings is None:
            return []
        return self.settings[self.channel-1].spike_windows
    
    def _set_windows(self, value):
        if self.settings is None:
            return
        self.settings[self.channel-1].spike_windows = value

    def _channel_changed(self, new):
        self.plot.channel = self.channels[new-1]

    def _plot_default(self):
        # Create the plot
        index_mapper = LinearMapper(range=DataRange1D(low=0, high=0.0012))
        value_mapper = LinearMapper(range=DataRange1D(low=-0.00025, high=0.00025))
        plot = SnippetChannelPlot(history=20,
                channel=self.channels[self.channel-1],
                value_mapper=value_mapper, 
                index_mapper=index_mapper,
                bgcolor='white', padding=[60, 5, 5, 20])
        add_default_grids(plot, major_index=1e-3, minor_index=1e-4,
                major_value=1e-3, minor_value=1e-4)

        # Add the axes labels
        axis = PlotAxis(orientation='left', component=plot,
                tick_label_formatter=scale_formatter, title='Signal (mV)')
        plot.overlays.append(axis)
        axis = PlotAxis(orientation='bottom', component=plot, 
                tick_label_formatter=scale_formatter)
        plot.overlays.append(axis)

        # Add the tools
        zoom = ZoomTool(plot, drag_button=None, axis="value")
        plot.overlays.append(zoom)
        self.tool = WindowTool(component=plot)
        plot.overlays.append(self.tool)
        
        # Whenever we draw a window, the settings should immediately be
        # updated!
        self.sync_trait('windows', self.tool)
        return plot
    
    THRESHOLD_EDITOR = RangeEditor(low=-5e-4*VOLTAGE_SCALE, 
                                   high=5e-4*VOLTAGE_SCALE)

    traits_view = View(
            VGroup(
                #Item('channel'),
                HGroup(
                    Item('channel', style='text', show_label=False, width=-25),
                    Item('sign', label='Signed?'),
                    Item('threshold', editor=THRESHOLD_EDITOR, show_label=False, springy=True),
                    ),
                Item('plot', editor=ComponentEditor(width=250, height=250)),
                show_labels=False,
                ),
            )

class PhysiologyExperimentMixin(HasTraits):

    # Acquire physiology?
    spool_physiology         = Bool(False)
    physiology_settings      = Instance(PhysiologyParadigmMixin, ())

    physiology_container     = Instance(Component)
    physiology_plot          = Instance(Component)
    physiology_index_range   = Instance(ChannelDataRange)
    physiology_value_range   = Instance(DataRange1D, ())

    physiology_channel_span  = Float(0.5e-3)

    physiology_window_1      = Instance(SortWindow)
    physiology_window_2      = Instance(SortWindow)
    physiology_window_3      = Instance(SortWindow)
    
    
    # Overlays
    spike_overlay            = Instance(SpikeOverlay)
    threshold_overlay        = Instance(ThresholdOverlay)
    
    # Show the overlays?
    visualize_spikes         = Bool(True)
    visualize_thresholds     = Bool(False)

    @on_trait_change('data')
    def _physiology_sort_plots(self):
        settings = self.physiology_settings.channel_settings
        channels = self.data.physiology_spikes
        
        window = SortWindow(channel=1, settings=settings, channels=channels)
        self.physiology_window_1 = window
        window = SortWindow(channel=5, settings=settings, channels=channels)
        self.physiology_window_2 = window
        window = SortWindow(channel=9, settings=settings, channels=channels)
        self.physiology_window_3 = window

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
        # Padding is in left, right, top, bottom order
        container = OverlayPlotContainer(padding=[50, 20, 20, 50])

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
        container.add(plot)

        self._add_behavior_plots(index_mapper, container)

        # Create the neural plots
        value_mapper = LinearMapper(range=self.physiology_value_range)
        plot = ExtremesChannelPlot(channel=self.data.physiology_processed, 
                index_mapper=index_mapper, value_mapper=value_mapper)
        plot.overlays.append(ChannelNumberOverlay(plot=plot))
        container.add(plot)
        add_default_grids(plot, major_index=1, minor_index=0.25,
                major_value=1e-3, minor_value=1e-4)
        axis = PlotAxis(component=plot, orientation='left',
                tick_label_formatter=scale_formatter, title='Volts (mV)')
        plot.underlays.append(axis)
        add_time_axis(plot, 'bottom', fraction=True)
        self.physiology_plot = plot

        tool = MultiChannelRangeTool(component=plot)
        plot.tools.append(tool)

        overlay = SpikeOverlay(plot=plot, spikes=self.data.physiology_spikes)
        self.sync_trait('visualize_spikes', overlay, 'visible', mutual=False)
        plot.overlays.append(overlay)
        self.spike_overlay = overlay
        overlay = ThresholdOverlay(plot=plot, visible=False)
        self.sync_trait('visualize_thresholds', overlay, 'visible', mutual=False)
        self.physiology_settings.sync_trait('spike_thresholds', overlay,
                                            'thresholds', mutual=False)
        self.physiology_settings.sync_trait('spike_signs', overlay,
                                            'signs', mutual=False)
        plot.overlays.append(overlay)
        self.threshold_overlay = overlay

        self.physiology_container = container
        self._physiology_value_range_update()

    def _add_behavior_plots(self, index_mapper, container):
        pass

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
                editor=RangeEditor(low=0.1, high=30.0)),
            Item('object.physiology_index_range.trig_delay',
                label='Trigger delay',
                editor=RangeEditor(low=0.0, high=10.0)),
            Item('physiology_channel_span', label='Y span',
                editor=RangeEditor(low=0, high=5e-3)),
            label='Plot Settings',
            show_border=True,
            )

    physiology_view = View(
            HSplit(
                Tabbed(
                    Include('physiology_settings_group'),
                    VGroup(
                        HGroup(
                            Item('visualize_spikes', label='Show sorted spikes?'),
                            Item('visualize_thresholds', label='Show sort threshold?'),
                            show_border=True,
                            ),
                        Item('physiology_window_1', style='custom', width=250),
                        Item('physiology_window_2', style='custom', width=250),
                        Item('physiology_window_3', style='custom', width=250),
                        show_labels=False,
                        ),
                    VGroup(
                        Item('object.threshold_overlay', style='custom'),
                        Item('object.spike_overlay', style='custom'),
                        show_labels=False,
                        ),
                    ),
                Item('physiology_container', 
                    editor=ComponentEditor(width=1200, height=800), 
                    width=1200,
                    resizable=True),
                show_labels=False,
                ),
            resizable=True)

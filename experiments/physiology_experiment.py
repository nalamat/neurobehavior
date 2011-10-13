import numpy as np
from enthought.enable.api import Component, ComponentEditor
from enthought.chaco.api import (LinearMapper, DataRange1D,
        OverlayPlotContainer)
from enthought.traits.ui.api import VGroup, HGroup, Item, Include, View, \
        InstanceEditor, RangeEditor, HSplit, Tabbed
from enthought.traits.api import Instance, HasTraits, Float, DelegatesTo, \
     Bool, on_trait_change, Int, on_trait_change, Any, Range, Event, Property,\
     Tuple, List, cached_property, Button, Enum
from enthought.traits.ui.api import RangeEditor

from physiology_paradigm import PhysiologyParadigm
from physiology_data import PhysiologyData
from physiology_controller import PhysiologyController

from enthought.chaco.api import PlotAxis, VPlotContainer, PlotAxis
from enthought.chaco.tools.api import ZoomTool
from cns.chaco_exts.tools.window_tool import WindowTool
from cns.chaco_exts.helpers import add_default_grids, add_time_axis
from cns.chaco_exts.channel_data_range import ChannelDataRange
from cns.chaco_exts.timeseries_plot import TimeseriesPlot
from cns.chaco_exts.extremes_multi_channel_plot import ExtremesMultiChannelPlot
from cns.chaco_exts.ttl_plot import TTLPlot
from cns.chaco_exts.epoch_plot import EpochPlot
from cns.chaco_exts.channel_range_tool import MultiChannelRangeTool
from cns.chaco_exts.channel_number_overlay import ChannelNumberOverlay
from cns.chaco_exts.snippet_channel_plot import SnippetChannelPlot
from cns import get_config

from cns.chaco_exts.spike_overlay import SpikeOverlay
from cns.chaco_exts.threshold_overlay import ThresholdOverlay

CHANNELS = get_config('PHYSIOLOGY_CHANNELS')
VOLTAGE_SCALE = 1e3
scale_formatter = lambda x: "{:.2f}".format(x*VOLTAGE_SCALE)

from enthought.traits.ui.menu import MenuBar, Menu, ActionGroup, Action

def create_menubar():
    actions = ActionGroup(
            Action(name='Load settings', action='load_settings'),
            Action(name='Save settings as', action='saveas_settings'),
            Action(name='Restore defaults', action='reset_settings'),
            )
    menu = Menu(actions, name='&Physiology')
    return MenuBar(menu)

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
        
        # Whenever we draw a window, the settings should immediately be updated!
        self.sync_trait('windows', self.tool)
        return plot
    
    THRESHOLD_EDITOR = RangeEditor(low=-5e-4*VOLTAGE_SCALE, 
                                   high=5e-4*VOLTAGE_SCALE)

    traits_view = View(
            VGroup(
                HGroup(
                    Item('channel', style='text', show_label=False, width=-25),
                    Item('sign', label='Signed?'),
                    Item('threshold', editor=THRESHOLD_EDITOR, show_label=False,
                         springy=True),
                    ),
                Item('plot', editor=ComponentEditor(width=250, height=250)),
                show_labels=False,
                ),
            )

class PhysiologyExperiment(HasTraits):

    settings                 = Instance(PhysiologyParadigm, ())
    data                     = Instance(PhysiologyData)

    physiology_container     = Instance(Component)
    physiology_plot          = Instance(Component)
    physiology_index_range   = Instance(ChannelDataRange)
    physiology_value_range   = Instance(DataRange1D, ())
    channel_span             = Float(0.5e-3)

    sort_window_1            = Instance(SortWindow)
    sort_window_2            = Instance(SortWindow)
    sort_window_3            = Instance(SortWindow)
    channel_sort             = Property(depends_on='sort_window_+.channel')

    channel                 = Enum('processed', 'raw')
    channel_mode            = Enum('TDT', 'TBSI', 'Test')

    # Overlays
    spike_overlay            = Instance(SpikeOverlay)
    threshold_overlay        = Instance(ThresholdOverlay)
    parent                   = Any
    
    # Show the overlays?
    visualize_spikes         = Bool(False)
    visualize_thresholds     = Bool(False)
    show_channel_number      = Bool(True)

    @cached_property
    def _get_channel_sort(self):
        channels = []
        for i in range(3):
            window = getattr(self, 'sort_window_{}'.format(i+1))
            # The GUI representation starts at 1, the program representation
            # starts at 0.  For 16 channels, the GUI displays the numbers 1
            # through 16 which corresponds to 0 through 15 in the code.  We need
            # to convert back and forth as needed.
            channels.append(window.channel-1)
        return channels

    @on_trait_change('data, settings.channel_settings')
    def _physiology_sort_plots(self):
        settings = self.settings.channel_settings
        channels = self.data.spikes
        window = SortWindow(channel=1, settings=settings, channels=channels)
        self.sort_window_1 = window
        window = SortWindow(channel=5, settings=settings, channels=channels)
        self.sort_window_2 = window
        window = SortWindow(channel=9, settings=settings, channels=channels)
        self.sort_window_3 = window

    def _channel_changed(self, new):
        if new == 'raw':
            self.physiology_plot.channel = self.data.raw
        else:
            self.physiology_plot.channel = self.data.processed

    @on_trait_change('data, parent')
    def _generate_physiology_plot(self):
        # NOTE THAT ORDER IS IMPORTANT.  First plots added are at bottom of
        # z-stack, so the physiology must be last so it appears on top.

        # Padding is in left, right, top, bottom order
        container = OverlayPlotContainer(padding=[50, 20, 20, 50])

        # Create the index range shared by all the plot components
        self.physiology_index_range = ChannelDataRange(span=5, trig_delay=1,
                timeseries=self.data.ts,
                sources=[self.data.processed])

        # Create the TTL plot
        index_mapper = LinearMapper(range=self.physiology_index_range)
        value_mapper = LinearMapper(range=DataRange1D(low=0, high=1))
        plot = TTLPlot(channel=self.data.sweep,
                index_mapper=index_mapper, value_mapper=value_mapper,
                reference=0, fill_color=(0.25, 0.41, 0.88, 0.1),
                line_color='transparent', rect_center=0.5, rect_height=1.0)
        container.add(plot)

        # Create the epoch plot
        plot = EpochPlot(series=self.data.epoch, marker='diamond',
                marker_color=(.5, .5, .5, 1.0), marker_height=0.9,
                marker_size=10,
                index_mapper=index_mapper, value_mapper=value_mapper)
        container.add(plot)

        add_default_grids(plot, major_index=1, minor_index=0.25)

        # Hack alert.  Can we separate this out into a separate function?
        if self.parent is not None:
            try:
                self.parent._add_behavior_plots(index_mapper, container)
            except AttributeError:
                pass

        # Create the neural plots
        value_mapper = LinearMapper(range=self.physiology_value_range)
        plot = ExtremesMultiChannelPlot(channel=self.data.processed, 
                index_mapper=index_mapper, value_mapper=value_mapper)
        self.settings.sync_trait('visible_channels', plot, 'channel_visible', mutual=False)

        overlay = ChannelNumberOverlay(plot=plot)
        self.sync_trait('show_channel_number', overlay, 'visible')
        plot.overlays.append(overlay)

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

        overlay = SpikeOverlay(plot=plot, spikes=self.data.spikes)
        self.sync_trait('visualize_spikes', overlay, 'visible')
        plot.overlays.append(overlay)
        self.spike_overlay = overlay
        
        # Create the threshold overlay plot
        overlay = ThresholdOverlay(plot=plot, visible=False)
        self.sync_trait('visualize_thresholds', overlay, 'visible')
        self.settings.sync_trait('spike_thresholds', overlay, 'sort_thresholds', mutual=False)
        self.settings.sync_trait('spike_signs', overlay, 'sort_signs', mutual=False)
        self.sync_trait('channel_sort', overlay, 'sort_channels', mutual=False)
        plot.overlays.append(overlay)
        self.threshold_overlay = overlay

        self.physiology_container = container

    zero_delay = Button('Reset trigger delay')
    pause_update = Button('Pause update')
    resume_update = Button('Resume update')

    def _zero_delay_fired(self):
        self.physiology_index_range.trig_delay = 0

    def _pause_update_fired(self):
        current_trigger = len(self.data.ts)
        self.physiology_index_range.trigger = current_trigger

    def _resume_update_fired(self):
        self.physiology_index_range.trigger = -1

    @on_trait_change('parent.selected_trial')
    def _update_selected_trigger(self, new):
        self.physiology_index_range.update_mode = 'triggered'
        self.physiology_index_range.trigger = new

    trigger_buttons = HGroup(
            'zero_delay',
            'pause_update',
            'resume_update',
            show_labels=False,
            )

    physiology_settings_group = VGroup(
            HGroup(
                Item('show_channel_number', label='Show channel number'),
                Item('channel'),
                Item('channel_mode'),
                ),
            Item('settings', style='custom',
                editor=InstanceEditor(view='physiology_view')),
            Include('physiology_view_settings_group'),
            show_border=True,
            show_labels=False,
            label='Channel settings'
            )

    physiology_view_settings_group = VGroup(
            Include('trigger_buttons'),
            Item('object.physiology_index_range.update_mode', 
                label='Trigger mode'),
            Item('object.physiology_index_range.span',
                label='X span',
                editor=RangeEditor(low=0.1, high=30.0)),
            Item('channel_span', label='Y span',
                editor=RangeEditor(low=0, high=5e-3)),
            Item('object.physiology_index_range.trig_delay',
                label='Trigger delay'),
            Item('object.physiology_index_range.trigger',
                label='Trigger number'),
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
                        Item('sort_window_1', style='custom', width=250),
                        Item('sort_window_2', style='custom', width=250),
                        Item('sort_window_3', style='custom', width=250),
                        show_labels=False,
                        label='Sort settings'
                        ),
                    VGroup(
                        Item('object.threshold_overlay', style='custom'),
                        Item('object.spike_overlay', style='custom'),
                        Item('object.physiology_plot', style='custom'),
                        show_labels=False,
                        label='GUI settings'
                        ),
                    ),
                Item('physiology_container', 
                    editor=ComponentEditor(width=500, height=800), 
                    width=500,
                    resizable=True),
                show_labels=False,
                ),
            menubar=create_menubar(),
            handler=PhysiologyController,
            resizable=True,
            height=0.95,
            width=0.95,
            )

if __name__ == '__main__':
    import tables
    from cns import get_config
    from os.path import join
    from tdt import DSPProject

    tempfile = join(get_config('TEMP_ROOT'), 'test_physiology.h5')
    datafile = tables.openFile(tempfile, 'w')
    data = PhysiologyData(store_node=datafile.root)
    addr = ('localhost', 13131)
    controller = PhysiologyController(process=DSPProject(address=addr))
    PhysiologyExperiment(data=data).configure_traits(handler=controller)

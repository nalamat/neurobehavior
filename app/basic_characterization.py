#from enthought.etsconfig.api import ETSConfig
#ETSConfig.toolkit = 'qt4'
'''
Created on Jun 9, 2010

@author: admin_behavior
'''
import settings

from cns.chaco.extremes_channel_plot import ExtremesChannelPlot
from cns.chaco.channel_data_range import ChannelDataRange
from scipy.signal import filtfilt
from tdt import DSPProcess

from cns.channel import FileMultiChannel, MultiChannel, RAMMultiChannel, \
    RAMChannel, Channel
from cns.data.h5_utils import append_date_node
from enthought.pyface.timer.api import Timer
from enthought.traits.api import Range, Float, HasTraits, Instance, DelegatesTo, \
    Int, Any, on_trait_change, Enum, Trait, Tuple, List, Property, Str, \
    cached_property, Bool
from enthought.traits.ui.api import View, VGroup, HGroup, Action, Controller, \
        Item, TupleEditor, HSplit, VSplit, RangeEditor, Label
import numpy as np
import tables

from cns.pipeline import lfilter
from cns.traits.ui.api import ListAsStringEditor

class ChannelSetting(HasTraits):

    number          = Int
    differential    = Str
    visible         = Bool(True)

class MonitorSetting(HasTraits):

    number  = Int, Label
    channel = Range(1, 16, 1)
    gain    = Int(50e3)

    def __len__(self):
        return 1

from enthought.traits.ui.api import TableEditor, ObjectColumn
from enthought.traits.ui.extras.checkbox_column import CheckboxColumn

channel_editor = TableEditor(
        show_row_labels=True,
        sortable=False,
        columns=[
            ObjectColumn(name='number', editable=False, width=10, label=''),
            CheckboxColumn(name='visible', width=10, label=''), 
            ObjectColumn(name='differential'),
            ]
        )

monitor_editor = TableEditor(
        show_row_labels=True,
        sortable=False,
        columns=[
            ObjectColumn(name='number', editable=False, width=10, label=''),
            ObjectColumn(name='number', width=10, label=''),
            ObjectColumn(name='gain'),
            ]
        )

def to_list(string):
    '''
    Converts a string to a list of integers

    >>> to_list('11')
    [11]

    >>> to_list('1-4')
    [1, 2, 3, 4]

    >>> to_list('1, 3-6')
    [1, 3, 4, 5, 6]

    >>> to_list('1, 3-4, 10')
    [1, 3, 4, 10]

    >>> to_list('1, 3 - 4, 10')
    [1, 3, 4, 10]
    '''
    elements = [s.strip() for s in string.split(',')]
    indices = []
    for element in elements:
        if '-' in element:
            lb, ub = [int(e.strip()) for e in element.split('-')]
            indices.extend(range(lb, ub+1))
        elif element == '':
            pass
        else:
            indices.append(int(element))
    return indices

from enthought.enable.api import Component, ComponentEditor
from enthought.traits.ui.api import TextEditor
from cns.chaco.helpers import add_time_axis, add_default_grids

editor = []
for i in range(4):
    editor.append(TupleEditor(editors=[TextEditor(), TextEditor()]))

editor = TupleEditor(editors=editor)

class MedusaSettings(HasTraits):

    raw_data            = Instance(MultiChannel)
    raw_view            = Instance(Component)
    raw_plot            = Instance(ExtremesChannelPlot)
    index_range         = Instance(ChannelDataRange)


    def set_visible_channels(self, value):
        self.model.raw_plot.visible = value


    # We can monitor up to four channels.  These map to DAC outputs 9, 10, 11
    # and 12 on the RZ5.  The first output (9) also goes to the speaker.
    monitor_settings    = List(Instance(MonitorSetting))

    # We adjust two key settings, whether the channel is visible in the plot and
    # the differentials to apply to it.
    channel_settings    = List(Instance(ChannelSetting))

    plot_mode           = Enum('continuous', 'triggered')

    def _index_range_default(self):
        return ChannelDataRange(range=10, interval=8)

    def _monitor_settings_default(self):
        return [MonitorSetting(number=i) for i in range(1, 5)]

    def _channel_settings_default(self):
        return [ChannelSetting(number=i) for i in range(1, 17)]

    # List of the channels visible in the plot
    visible_channels = Property(depends_on='channel_settings.visible')

    @cached_property
    def _get_visible_channels(self):
        return [i for i, ch in enumerate(self.channel_settings) if ch.visible]

    # Generates the matrix that will be used to compute the differential for the
    # channels.  This matrix will be uploaded to the RZ5.
    diff_matrix = Property(depends_on='channel_settings.differential')

    @cached_property
    def _get_diff_matrix(self):
        n_chan = len(self.channel_settings)
        map = np.zeros((n_chan, n_chan))
        for channel in self.channel_settings:
            channels = to_list(channel.differential)
            if len(channels) != 0:
                sf = -1.0/len(channels)
                for d in channels:
                    map[channel.number, d-1] = sf
        return map

    # When the visible channels change, we need to update the plot!
    @on_trait_change('visible_channels')
    def _update_plot(self):
        self.raw_plot.visible = self.visible_channels

    # If plot offset or number of visible channels change, we need to update the
    # value range accordingly.
    @on_trait_change('visible_channels, plot_offset')
    def _update_range(self):
        offset = self.raw_plot.offset
        self.range.high_setting = offset*len(self.visible_channels)

    # Filter cutoff
    fc_low      = Float(10e3)
    fc_high     = Float(300)

    file = Any

    def _file_default(self):
        return tables.openFile('basic_characterization.h5', 'w')

    def _raw_data_default(self):
        #return FileMultiChannel(channels=16, node=self.file.root,
        #        name='raw_data', compression_level=0)
        return RAMMultiChannel(channels=16, fs=25e3)

    def _raw_plot_default(self):
        self.index_range.sources = [self.raw_data]
        index_mapper = LinearMapper(range=self.index_range)
        value_range = DataRange1D(low_setting=-0.3e-3, high_setting=0.6e-3)
        value_mapper = LinearMapper(range=value_range)
        plot = ExtremesChannelPlot(channel=self.raw_data, 
                index_mapper=index_mapper, value_mapper=value_mapper,
                visible=self.visible_channels)
        add_default_grids(plot, major_index=1, minor_index=0.25)
        add_time_axis(plot)
        self.range = value_range
        return plot

    def _raw_view_default(self):
        container = OverlayPlotContainer(bgcolor='white', fill_padding=True,
                padding=50)
        container.add(self.raw_plot)
        return container

    plot_offset = DelegatesTo('raw_plot', 'offset')
    time_range = DelegatesTo('index_range', 'range')
    time_interval = DelegatesTo('index_range', 'interval')

    traits_view = View(
            HSplit(
                VGroup(
                    HGroup(
                        Item('fc_high'), 
                        Label('to'), 
                        Item('fc_low'),
                        Label('Hz'),
                        show_labels=False,
                        label='Filter Settings',
                        show_border=True,
                        ),
                    VGroup(
                        Item('monitor_settings', show_label=False, 
                             editor=monitor_editor, height=-100),
                        label='Monitor Settings',
                        show_border=True),
                    VGroup(
                        Item('channel_settings', editor=channel_editor,
                             show_label=False),
                        label='Channel configuration', show_border=True
                        ),
                    ),
                VGroup(
                    HGroup(
                        Item('plot_mode', label='Update mode'),
                        Item('plot_offset', label='Channel spacing'),
                        Item('time_range', label='Range'),
                        Item('time_interval', label='Update interval'),
                        ),
                    Item('raw_view', editor=ComponentEditor(),
                         show_label=False, width=1000, height=600),
                    ),
                ),
            resizable=True,
            )

from enthought.chaco.api import OverlayPlotContainer, LinearMapper, \
        DataRange1D, PlotAxis, PlotGrid

from cns import RCX_ROOT
from os.path import join

class MedusaController(Controller):
    
    plot = Any

    pipeline_   = Any
    iface_      = Any
    buffer_     = Any
    timer       = Instance(Timer)

    process             = Any
    iface_physiology    = Any
    iface_signal        = Any
    buffer_raw          = Any
    buffer_processed    = Any
    pipeline_raw        = Any
    pipeline_processed  = Any

    def _process_default(self):
        return DSPProcess()

    #def _iface_signal_default(self):
    #    circuit = join(RCX_ROOT, 'physiology')
    #    return self.process.load_circuit(circuit, 'RZ6')

    def _iface_physiology_default(self):
        circuit = join(RCX_ROOT, 'physiology')
        return self.process.load_circuit(circuit, 'RZ6')

    def _buffer_raw_default(self):
        print 'getting buffer'
        return self.iface_physiology.get_buffer('cfiltered', 'r',
                src_type='int16', dest_type='float32', channels=16) 

    def init(self, info=None):
        self.model = info.object
        print self.iface_physiology
        print self.buffer_raw
        self.model.raw_data.fs = self.buffer_raw.fs
        self.process.start()
        self.timer = Timer(500, self.tick)

    def _pipeline_processed_default(self):
        return self.model.processed_data

    def _pipeline_raw_default(self):
        return self.model.raw_data

    def tick(self):
        data = self.buffer_raw.read()
        if not len(data) == 0:
            self.pipeline_raw.send(data)

    @on_trait_change('object.setting.fc_high')
    def set_fc_high(self, value):
        self.iface_physiology.set_tag('FiltHP', value)

    @on_trait_change('object.setting.fc_low')
    def set_fc_low(self, value):
        self.iface_physiology.set_tag('FiltLP', value)

def test_medusa():
    #MedusaSettings().configure_traits()
    MedusaSettings().configure_traits(handler=MedusaController())

if __name__ == '__main__':
    #test_medusa()
    import sys, cProfile
    cProfile.run('test_medusa()', 'profile.dmp')
    import pstats
    p = pstats.Stats('profile.dmp')
    p.sort_stats('cumulative').print_stats(50)

#from enthought.etsconfig.api import ETSConfig
#ETSConfig.toolkit = 'qt4'
'''
Created on Jun 9, 2010

@author: admin_behavior
'''
import settings

from scipy.signal import filtfilt
from tdt import DSPProcess as DSPProcess

from cns.channel import FileMultiChannel, MultiChannel, RAMMultiChannel, \
    RAMChannel, Channel
from cns.data.h5_utils import append_date_node
from enthought.pyface.timer.api import Timer
from enthought.traits.api import Range, Float, HasTraits, Instance, DelegatesTo, \
    Int, Any, on_trait_change, Enum, Trait, Tuple, List, Property, Str, \
    cached_property, Bool
from enthought.traits.ui.api import View, VGroup, HGroup, Action, Controller, \
        Item, TupleEditor, HSplit, VSplit
import numpy as np
import tables

from cns.pipeline import lfilter
from cns.traits.ui.api import ListAsStringEditor

class ChannelSetting(HasTraits):

    number          = Int
    differential    = Str
    visible         = Bool(True)

class MonitorSetting(HasTraits):

    channel = Range(1, 16, 1)
    gain    = Int(50e3)

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
            ObjectColumn(name='number'),
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

editor = []
for i in range(4):
    editor.append(TupleEditor(editors=[TextEditor(), TextEditor()]))

editor = TupleEditor(editors=editor)

class MedusaSettings(HasTraits):

    raw_data    = Instance(MultiChannel)
    raw_view    = Instance(Component)

    monitor_settings    = List(Instance(MonitorSetting))
    channel_settings    = List(Instance(ChannelSetting))

    def _monitor_settings_default(self):
        return [MonitorSetting(number=i) for i in range(1, 5)]

    def _channel_settings_default(self):
        return [ChannelSetting(number=i) for i in range(1, 17)]

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

    visible = Property(depends_on='channel_settings.visible')

    @cached_property
    def _get_visible(self):
        return [setting.visible for setting in self.channel_settings]

    attenuation = Range(0.0, 120.0, 20.0)
    fc_low      = Float(10e3)
    fc_high     = Float(300)
    trial_dur   = Float(5)
    filt_coeffs = Property(depends_on='fc_low, fc_high')

    @cached_property
    def _get_filt_coeffs(self):
        from scipy import signal
        Wn = self.fc_high/25e3, self.fc_low/25e3
        return signal.butter(4, Wn, 'band')

    file = Any

    def _file_default(self):
        return tables.openFile('basic_characterization.h5', 'w')

    def _raw_data_default(self):
        return FileMultiChannel(channels=16, node=self.file.root,
                name='raw_data', compression_level=0)

    def _processed_data_default(self):
        return FileMultiChannel(channels=16, fs=self.iface_physiology.fs,
                node=self.file.root, name='processed_data')

    def _raw_view_default(self):
        container = OverlayPlotContainer(bgcolor='white', fill_padding=True,
                padding=50)

        index_range = ChannelDataRange(sources=[self.raw_data], range=12,
                interval=10)
        index_mapper = LinearMapper(range=index_range)
        value_range = DataRange1D(low_setting=-1.3e-3, high_setting=9.3e-3)
        value_mapper = LinearMapper(range=value_range)
        plot = ExtremesChannelPlot(channel=self.raw_data,
                index_mapper=index_mapper, value_mapper=value_mapper)
        grid = PlotGrid(mapper=plot.index_mapper, component=plot,
                orientation='vertical', line_color='lightgray',
                line_style='dot', grid_interval=0.25)
        plot.underlays.append(grid)
        grid = PlotGrid(mapper=plot.index_mapper, component=plot,
                orientation='vertical', line_color='lightgray',
                line_style='solid', grid_interval=1)
        plot.underlays.append(grid)
        axis = PlotAxis(component=plot, title="Time (s)", orientation="top")
        plot.underlays.append(axis)
        plot.underlays.append(axis)
        self.plot = plot
        container.add(plot)
        return container

    traits_view = View(
            HSplit(
                VGroup(
                    VGroup(
                        Item('monitor_settings', show_label=False, 
                             editor=monitor_editor),
                        label='Monitor Settings',
                        show_border=True),
                    VGroup(
                        Item('channel_settings', editor=channel_editor,
                             show_label=False),
                        label='Channel configuration', show_border=True
                        ),
                    'fc_low{Lowpass cutoff (Hz)}',
                    'fc_high{Highpass cutoff (Hz)}',
                    'trial_dur{Trial duration (s)}',
                    ),
                Item('raw_view', editor=ComponentEditor(),
                     show_label=False, width=1000, height=600),
                ),
            resizable=True,
            )

from enthought.chaco.api import OverlayPlotContainer, LinearMapper, \
        DataRange1D, PlotAxis, PlotGrid
from cns.chaco.extremes_channel_plot import ExtremesChannelPlot
from cns.chaco.channel_data_range import ChannelDataRange

class MedusaController(Controller):
    
    plot = Any

    pipeline_   = Any
    iface_      = Any
    buffer_     = Any
    timer       = Instance(Timer)

    iface_physiology    = Any
    buffer_raw          = Any
    buffer_processed    = Any
    pipeline_raw        = Any
    pipeline_processed  = Any
    
    def init(self, info=None):
        self.circuit = DSPProcess('components/physiology', 'RZ5')
        self.buffer_raw = self.circuit.get_buffer('craw', 'r', src_type='int16',
                dest_type='float32', channels=16) 
        self.model.raw_data.fs = self.buffer_raw.fs
        self.circuit.start()

    def _pipeline_processed_default(self):
        return self.model.processed_data

    def _pipeline_raw_default(self):
        return self.model.raw_data

    def init(self, info):
        self.timer = Timer(100, self.tick)
        self.model = info.object

    def tick(self):
        data = self.buffer_raw.read()
        if not len(data) == 0:
            self.pipeline_raw.send(data)
    
    def object_attenuation_changed(self, value):
        print 'setting attneuation'
        self.iface_RZ6.set_tag('sig_atten', value)
    
    @on_trait_change('setting.fc_high')
    def set_highpass_frequency(self, value):
        self.iface_physiology.set_tag('FiltHP', value)

    @on_trait_change('object.setting.fc_low')
    def set_lowpass_frequency(self, value):
        self.iface_physiology.set_tag('FiltLP', value)

def test_medusa():
    MedusaSettings().configure_traits(handler=MedusaController())

if __name__ == '__main__':
    #test_medusa()
    import sys, cProfile
    cProfile.run('test_medusa()', 'profile.dmp')
    import pstats
    p = pstats.Stats('profile.dmp')
    p.sort_stats('cumulative').print_stats(50)

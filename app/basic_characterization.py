#from enthought.etsconfig.api import ETSConfig
#ETSConfig.toolkit = 'qt4'
'''
Created on Jun 9, 2010

@author: admin_behavior
'''
import settings

from scipy.signal import filtfilt
#from tdt import DSPProcess
from tdt import DSPCircuit as DSPProcess

from cns.channel import FileMultiChannel, MultiChannel, RAMMultiChannel, \
    RAMChannel, Channel
from cns.data.h5_utils import append_date_node
from enthought.pyface.timer.api import Timer
from enthought.traits.api import Range, Float, HasTraits, Instance, DelegatesTo, \
    Int, Any, on_trait_change, Enum, Trait, Tuple, List, Property, Str, \
    cached_property, Bool
from enthought.traits.ui.api import View, VGroup, HGroup, Action, Controller, \
Item, TupleEditor
import numpy as np
import tables

from cns.pipeline import lfilter
from cns.traits.ui.api import ListAsStringEditor

class ChannelSetting(HasTraits):

    number          = Int
    differential    = Str
    visible         = Bool(True)

    view = View(
            HGroup(
                Item('number', style='readonly'),
                Item('visible'),
                Item('differential'),
                show_labels=False,
                ),
            )

from enthought.traits.ui.api import TableEditor, ObjectColumn
from enthought.traits.ui.extras.checkbox_column import CheckboxColumn

table_editor = TableEditor(
        columns=[
            CheckboxColumn(name='visible', width=20),
            ObjectColumn(name='number'),
            ObjectColumn(name='differential'),
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

from enthought.enable.api import ComponentEditor

class MedusaSettings(HasTraits):

    # IN settings
    ch_out      = Tuple(Tuple(Range(1, 16,  1), Float(50e3)),
                        Tuple(Range(1, 16,  5), Float(50e3)),
                        Tuple(Range(1, 16,  9), Float(50e3)),
                        Tuple(Range(1, 16, 13), Float(50e3)))

    channels    = List(Instance(ChannelSetting))

    def _channels_default(self):
        return [ChannelSetting(number=i) for i in range(16)]

    #diff        = Tuple(*CH_DIFF)
    diff_matrix = Property(depends_on='channels.differential')

    @cached_property
    def _get_diff_matrix(self):
        n_chan = len(self.channels)
        map = np.zeros((n_chan, n_chan))
        for channel in self.channels:
            channels = to_list(channel.differential)
            if len(channels) != 0:
                sf = -1.0/len(channels)
                for d in channels:
                    map[channel.number, d-1] = sf
        return map

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

    traits_view = View(
            HGroup(
                VGroup(
                    VGroup(
                        Item('ch_out', show_label=False),
                        label='Monitor Channels',
                        show_border=True),
                    VGroup(
                        Item('channels', editor=table_editor, show_label=False),
                        label='Channel configuration', show_border=True
                        ),
                    'fc_low{Lowpass cutoff (Hz)}',
                    'fc_high{Highpass cutoff (Hz)}',
                    'trial_dur{Trial duration (s)}',
                    ),
                Item('handler.raw_view', editor=ComponentEditor(),
                    show_label=False, width=800, height=600),
                ),
            resizable=True,
            )

from enthought.chaco.api import OverlayPlotContainer, LinearMapper, \
        DataRange1D, PlotAxis, PlotGrid
from cns.chaco.extremes_channel_plot import ExtremesChannelPlot
from cns.chaco.channel_data_range import ChannelDataRange

class MedusaController(Controller):
    
    raw_data    = Instance(MultiChannel)
    processed_data = Instance(MultiChannel)
    raw_view    = Instance(OverlayPlotContainer)
    file = Any
    
    def _file_default(self):
        return tables.openFile('basic_characterization.h5', 'w')

    def _raw_data_default(self):
        return FileMultiChannel(channels=16, fs=self.iface_physiology.fs,
                node=self.file.root, name='raw_data', compression_level=0)

    def _processed_data_default(self):
        return FileMultiChannel(channels=16, fs=self.iface_physiology.fs,
                node=self.file.root, name='processed_data')

    pipeline_   = Any
    iface_      = Any
    buffer_     = Any
    timer       = Instance(Timer)
    settings    = Instance(MedusaSettings, args=())

    iface_physiology = Any
    buffer_raw          = Any
    buffer_processed    = Any
    pipeline_raw        = Any
    pipeline_processed  = Any

    def _pipeline_processed_default(self):
        return self.processed_data

    def _pipeline_raw_default(self):
        return self.raw_data

    def _iface_physiology_default(self):
        circuit = DSPProcess('components/physiology', 'RZ5')
        self.buffer_raw = circuit.get_buffer('craw', 'r', src_type='int16',
                dest_type='float32', channels=16) 
        #self.buffer_processed = circuit.get_buffer('processed', 'r', channels=16) 
        circuit.start()
        return circuit

    def _raw_view_default(self):
        container = OverlayPlotContainer(bgcolor='white', fill_padding=True,
                padding=50)

        index_range = ChannelDataRange(sources=[self.raw_data], range=10,
                interval=1)
        index_mapper = LinearMapper(range=index_range)
        value_range = DataRange1D(low_setting=-1.3e-3, high_setting=3.3e-3)
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
        axis = PlotAxis(component=plot, title="Time (s)", orientation="bottom")
        plot.underlays.append(axis)
        #axis = PlotAxis(component=plot, orientation="left")
        #plot.underlays.append(axis)
        #axis = PlotAxis(component=plot, orientation="right")
        #plot.underlays.append(axis)
        container.add(plot)
        return container

    def init(self, info):
        self.timer = Timer(100, self.tick)
        self.model = info.object

    def tick(self):
        data = self.buffer_raw.read()
        if not len(data) == 0:
            self.pipeline_raw.send(data)
        #data += np.dot(data.T, self.model.diff_matrix).T

    def set_attenuation(self, value):
        self.iface_RZ6.set_tag('sig_atten', value)
    
    def set_highpass_frequency(self, value):
        self.iface_physiology.set_tag('FiltHP', value)

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

    #import doctest
    #doctest.testmod()

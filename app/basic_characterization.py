'''
Created on Jun 9, 2010

@author: admin_behavior
'''
import settings

from tdt import DSPProcess

from cns.channel import FileMultiChannel, MultiChannel, RAMMultiChannel, \
    RAMChannel, Channel
from cns.data.h5_utils import append_date_node
from cns.widgets.views.channel_view import MultiChannelView
from enthought.pyface.timer.api import Timer
from enthought.traits.api import Range, Float, HasTraits, Instance, DelegatesTo, \
    Int, Any, on_trait_change, Enum, Trait, Tuple, List, Property, Str
from enthought.traits.ui.api import View, VGroup, HGroup, Action, Controller, \
Item, TupleEditor
import numpy as np
import tables

from cns.traits.ui.api import ListAsStringEditor

#CH_DIFF = [Range(0, 16, 4*int(i/4)+1) for i in range(16)]
#CH_DIFF = [List(Int, []) for i in range(16)]
CH_DIFF = [Str() for i in range(16)]
#CH_DIFF_EDITORS = [ListAsStringEditor() for i in range(len(CH_DIFF))]
CH_DIFF_LABELS = [str(i) for i in range(1, len(CH_DIFF)+1)]

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

class MedusaSettings(HasTraits):

    # IN settings
    ch_out      = Tuple(Tuple(Range(1, 16,  1), Float(50e3)),
                        Tuple(Range(1, 16,  5), Float(50e3)),
                        Tuple(Range(1, 16,  9), Float(50e3)),
                        Tuple(Range(1, 16, 13), Float(50e3)))

    diff        = Tuple(*CH_DIFF)
    diff_matrix = Property

    def _get_diff_matrix(self):
        n_chan = len(self.diff)
        map = np.zeros((n_chan, n_chan))
        for ch, diff in enumerate(self.diff):
            channels = to_list(diff)
            if len(channels) != 0:
                sf = -1.0/len(channels)
                for d in channels:
                    map[ch, d-1] = sf
        print map.ravel()
        return map.ravel()

    attenuation = Range(0.0, 120.0, 20.0)
    fc_low      = Float(3e3)
    fc_high     = Float(300)
    trial_dur   = Float(5)

    traits_view = View(
            HGroup(
                VGroup(
                    VGroup(
                        Item('ch_out', show_label=False),
                        label='Monitor Channels',
                        show_border=True),
                    VGroup(
                        Item('diff', show_label=False,
                             editor=TupleEditor(labels=CH_DIFF_LABELS)),
                        label='Differential Electrodes',
                        show_border=True),
                    'fc_low{Lowpass cutoff (Hz)}',
                    'fc_high{Highpass cutoff (Hz)}',
                    'trial_dur{Trial duration (s)}',
                    ),
                Item('handler.raw_view', style='custom'),
                ),
            resizable=True,
            )

class MedusaController(Controller):
    
    raw_data    = Instance(MultiChannel)
    processed_data = Instance(MultiChannel)
    raw_view    = Instance(MultiChannelView)
    file = Any
    
    def _file_default(self):
        return tables.openFile('basic_characterization.h5', 'w')

    def _raw_data_default(self):
        return FileMultiChannel(channels=16, fs=self.iface_physiology.fs,
                node=self.file.root, name='raw_data')

    def _processed_data_default(self):
        return FileMultiChannel(channels=16, fs=self.iface_physiology.fs,
                node=self.file.root, name='processed_data')

    pipeline_   = Any
    iface_      = Any
    buffer_     = Any
    timer       = Instance(Timer)
    settings    = Instance(MedusaSettings, args=())

    iface_physiology = Any
    buffer_raw = Any
    buffer_processed = Any
    pipeline_raw = Any
    pipeline_processed = Any

    def _pipeline_processed_default(self):
        return self.processed_data

    def _pipeline_raw_default(self):
        from cns.pipeline import diff
        return diff([], self.raw_data)

    def _iface_physiology_default(self):
        circuit = DSPProcess('components/physiology', 'RZ5')
        self.buffer_raw = circuit.get_buffer('raw', channels=16) 
        self.buffer_processed = circuit.get_buffer('processed', channels=16) 
        circuit.start()
        return circuit

    def _raw_view_default(self):
        return MultiChannelView(channel=self.raw_data, visual_aids=False)

    def init(self, info):
        self.timer = Timer(100, self.tick)

    def tick(self):
        self.pipeline_raw.send(self.buffer_raw.read())
        self.pipeline_processed.send(self.buffer_processed.read())

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
    p.strip_dirs().sort_stats('cumulative').print_stats(50)

    #import doctest
    #doctest.testmod()

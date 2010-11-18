'''
Created on Jun 9, 2010

@author: admin_behavior
'''
from config import settings

from cns import equipment
from cns.channel import FileMultiChannel, MultiChannel, RAMMultiChannel, \
    RAMChannel, Channel
from cns.data.h5_utils import append_date_node
from cns.signal.signal_dialog import SignalDialog
from cns.widgets.views.channel_view import MultiChannelView
from enthought.pyface.timer.api import Timer
from enthought.traits.api import Range, Float, HasTraits, Instance, DelegatesTo, \
    Int, Any, on_trait_change, Enum, Trait, Tuple, List, Property, Str
from enthought.traits.ui.api import View, VGroup, HGroup, Action, Controller, \
Item, TupleEditor
import numpy as np
import tables

modes = {'raw': 0,
         'differential': 1,
         'filtered': 2,
         'filtered differential': 3,
         'test spikes': 4,
         'test sinusoid': 5,
         }


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
    mode        = Trait('filtered', modes)
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

    #attenuation = Range(0.0, 120.0, 20.0)

    #ch_out      = Range(1, 16, 1)
    #ch_out_gain = Float(50e3)
    

    #ch_diff     = Range(1, 16, 1)

    #fc_low      = Float(3e3)
    #fc_high     = Float(300)

    # OUT settings
    #selector    = Instance(SignalDialog, {'allow_par': False})
    #signal      = DelegatesTo('selector')
    #trial_dur   = Float(5)

    # REPS
    #reps        = Int(-1)

    traits_view = View(
            VGroup(
                #'attenuation{Attenuation (dB SPL)}',
                'mode',
                VGroup(
                    Item('ch_out', show_label=False),
                    label='Monitor Channels',
                    show_border=True),
                VGroup(
                    Item('diff', show_label=False,
                         editor=TupleEditor(labels=CH_DIFF_LABELS)),
                    label='Differential Electrodes',
                    show_border=True),

                #'ch_out_gain{Monitor channel gain}',
                #'fc_low{Lowpass cutoff (Hz)}',
                #'fc_high{Highpass cutoff (Hz)}',
                #'trial_dur{Trial duration (s)}',
                #'reps{Repetitions (-1=infinite)}',
                #'selector{}@')
                ),
            )

class MedusaController(Controller):
    
    raw_data    = Instance(MultiChannel)
    raw_view    = Instance(MultiChannelView)

    def _raw_data_default(self):
        file = tables.openFile('basic_characterization.h5', 'w')
        return FileMultiChannel(channels=16, fs=self.RZ5.fs,
                                node=file.root, name='raw_data')

    def _raw_view_default(self):
        return MultiChannelView(channel=self.raw_data, visual_aids=False)

    RX6         = Any
    RZ5         = Any
    pipeline    = Any

    timer       = Instance(Timer)
    settings    = Instance(MedusaSettings, args=())
    prior       = Int(0)
    prior_sig   = Int(0)

    def _RZ5_default(self):
        circuit = equipment.dsp().load('physiology', 'RZ5')
        circuit.mc_sig.initialize(channels=16)
        circuit.mc_sig16.initialize(channels=16, src_type=np.int16, sf=8.19e7)
        circuit.start()
        return circuit
    
    @on_trait_change('settings.mode')
    def update_mode(self, new):
        self.RZ5.rec_mode.value = self.settings.mode_

    @on_trait_change('settings.ch_out')
    def update_ch_out(self, new):
        for i, (ch, gain) in enumerate(new):
            n = i+1 
            getattr(self.RZ5, 'ch_out_%d' % n).value = ch
            getattr(self.RZ5, 'ch_out_g_%d' % n).value = gain

    @on_trait_change('settings.diff')
    def update_ch_diff(self):
        self.RZ5.diff_map.set(self.settings.diff_matrix)
        print self.RZ5.diff_map.get()
        #self.RZ5.diff_gain.value = self.settings.diff_gain
    
    #@on_trait_change('settings.ch_diff')
    #def update_ch_differential(self, new):
    #    self.RZ5.ch_diff.value = new
    
    #@on_trait_change('settings.ch_out')
    #def update_ch_out(self, new):
    #    self.RZ5.ch_out.value = new
        
    #@on_trait_change('settings.attenuation')
    #def update_attenuation(self, new):
    #    equipment.dsp().set_attenuation(new, 'PA5')
    
    def init(self, info):
        # Load circuits
        
        #self.RX6 = equipment.dsp().init_device('RepeatPlayRecord', 'RX6')
        #self.RZ5 = equipment.dsp().init_device('physiology', 'RZ5')
        
        # Initialize buffers
        #self.RX6.sig_out.initialize(src_type=np.int8, sf=64)
        
        #self.pipeline = broadcast((self.raw_data, self.plot_data))
        #self.pipeline = self.plot_data
        self.timer = Timer(100, self.tick)

    def update_circuit(self):
        #equipment.atten().set_atten(self.settings.attenuation)

        #self.RX6.sig.set(self.settings.signal)
        #self.RX6.play_dur_n.value = len(self.settings.signal)
        #self.RX6.rec_dur_n.value = 0
        #self.RX6.reps.value = -1
        #self.RX6.trial_dur_n.set(self.settings.trial_dur, 's')

        #self.RZ5.f_lp.value = self.settings.fc_low
        #self.RZ5.f_hp.value = self.settings.fc_high
        #self.RZ5.ch_out.value = self.settings.ch_out
        #self.RZ5.ch_out_gain.value = self.settings.ch_out_gain
        pass

    def run(self, info):
        #self.update_circuit()
        #self.RX6.trigger(1)
        pass

    def tick(self):
        data = self.RZ5.mc_sig16.read()
        self.raw_data.send(data)
        #self.pipeline.send(data)
        #trig = int(self.RZ5.ts.value)
        
        #if self.prior != trig:
        #    self.plot_data.trigger_indices.append(trig)
        #    self.prior = trig
            
        #sig = self.RX6.sig_out.read()
        #self.plot_signal.send(sig)
        
        #trig = int(self.RX6.ts.value)
        #if self.prior_sig != trig:
        #    self.plot_signal.trigger_indices.append(trig)
        #    self.prior_sig = trig

plot_size = (300, 300)
view = View(
        HGroup(
            Item('handler.settings', style='custom'),
            Item('handler.raw_view', style='custom'),
            show_labels=False
            ),
        resizable=True,
        buttons=[Action(name='Run', action='run'),],
        height=1,
        width=1,
        )

def test_medusa():
    settings = MedusaSettings()
    handler = MedusaController(settings=settings)
    settings.configure_traits(handler=handler, view=view)

if __name__ == '__main__':
    test_medusa()
    #import sys, cProfile
    #cProfile.run('test_medusa()', 'profile.dmp')
    #import pstats
    #p = pstats.Stats('profile.dmp')
    #p.strip_dirs().sort_stats('cumulative').print_stats(50)

    #import doctest
    #doctest.testmod()

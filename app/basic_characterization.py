'''
Created on Jun 9, 2010

@author: admin_behavior
'''
import settings
from cns import equipment
from cns.channel import FileMultiChannel, MultiChannel, \
    RAMMultiChannel, RAMChannel, Channel
from cns.data.persistence import append_date_node
from cns.signal.signal_dialog import SignalDialog
from cns.widgets.views.channel_view import MultiChannelView
from enthought.pyface.timer.api import Timer
from enthought.traits.api import Range, Float, HasTraits, Instance, DelegatesTo, Int, Any
from enthought.traits.ui.api import View, VGroup, HGroup, Action, Controller
import numpy as np
import tables



class MedusaSettings(HasTraits):

    # IN settings
    attenuation = Range(0.0, 120.0, 20.0)
    ch_out      = Range(1, 16, 1)
    ch_out_gain = Float(50e3)

    fc_low      = Float(3e3)
    fc_high     = Float(300)

    # OUT settings
    selector    = Instance(SignalDialog, {'allow_par': False})
    signal      = DelegatesTo('selector')
    trial_dur   = Float(5)

    # REPS
    reps        = Int(-1)

    traits_view = View(
            VGroup(
                'attenuation{Attenuation (dB SPL)}',
                'ch_out{Monitor channel}',
                'ch_out_gain{Monitor channel gain}',
                'fc_low{Lowpass cutoff (Hz)}',
                'fc_high{Highpass cutoff (Hz)}',
                'trial_dur{Trial duration (s)}',
                'reps{Repetitions (-1=infinite)}',
                'selector{}@')
            )

class MedusaController(Controller):
    
    raw_data    = Instance(MultiChannel, ())
    plot_data   = Instance(MultiChannel, ())
    plot_signal = Instance(Channel, ())
    dec_data    = Instance(FileMultiChannel, ())
    raw_view    = Instance(MultiChannelView, ())

    RX6         = Any
    RZ5         = Any
    pipeline    = Any

    timer       = Instance(Timer)
    settings    = Instance(MedusaSettings, args=())
    prior       = Int(0)
    prior_sig       = Int(0)
    
    def init(self, info):
        # Load circuits
        file = tables.openFile('basic_characterization.h5', 'a')
        store_node = append_date_node(file.root)
        
        self.RX6 = equipment.dsp().init_device('RepeatPlayRecord', 'RX6')
        self.RZ5 = equipment.dsp().init_device('MedusaRecord_v4', 'RZ5')
        
        # Initialize buffers
        self.RX6.sig.initialize()
        self.RZ5.mc_sig.initialize(channels=16, read_mode='continuous')
        self.RZ5.mc_sig16.initialize(channels=16, read_mode='continuous', src_type=np.int16, 
                                     sf=81917500, compression='decimated')
        
        #self.raw_data = FileMultiChannel(channels=16, fs=self.RZ5.fs, name='mc_sig', 
        #                                 type=np.float32, node=store_node)
        #self.plot_data = BufferedMultiChannel(channels=16, fs=self.RZ5.fs, window=5)
        self.plot_data = RAMMultiChannel(channels=16, fs=self.RZ5.fs, window=10)
        self.plot_signal = RAMChannel(fs=self.RX6.fs, window=10)
        
        #self.raw_view = NewMultiChannelView(channel=self.plot_data, visual_aids=False)
        self.raw_view = MultiChannelView(signal=self.plot_signal,
                                         channel=self.plot_data, 
                                         visual_aids=False)
        #self.pipeline = broadcast((self.raw_data, self.plot_data))
        self.pipeline = self.plot_data
        self.timer = Timer(100, self.tick)

    def update_circuit(self):
        equipment.atten().set_atten(self.settings.attenuation)

        self.RX6.sig.set(self.settings.signal)
        self.RX6.play_dur_n.value = len(self.settings.signal)
        self.RX6.rec_dur_n.value = 0
        self.RX6.reps.value = -1
        self.RX6.trial_dur_n.set(self.settings.trial_dur, 's')

        self.RZ5.f_lp.value = self.settings.fc_low
        self.RZ5.f_hp.value = self.settings.fc_high
        self.RZ5.ch_out.value = self.settings.ch_out
        self.RZ5.ch_out_gain.value = self.settings.ch_out_gain

    def run(self, info):
        self.update_circuit()
        self.RX6.trigger(1)
        pass

    def tick(self):
        data = self.RZ5.mc_sig.read()
        #data = self.RZ5.mc_sig16.read()
        self.pipeline.send(data)
        trig = int(self.RZ5.ts.value)
        
        if self.prior != trig:
            self.plot_data.trigger_indices.append(trig)
            self.prior = trig
            
        sig = self.RX6.sig_out.read()
        self.plot_signal.send(sig)
        
        trig = int(self.RX6.ts.value)
        if self.prior_sig != trig:
            self.plot_signal.trigger_indices.append(trig)
            self.prior_sig = trig

plot_size = (300, 300)
view = View(
        HGroup('handler.settings{}@', 'handler.raw_view{}@'),
        resizable=True,
        buttons=[Action(name='Run', action='run'),],
        height=600,
        width=1200,
        )

def test_medusa():
    settings = MedusaSettings()
    handler = MedusaController(settings=settings)
    settings.configure_traits(handler=handler, view=view)

if __name__ == '__main__':
    test_medusa()

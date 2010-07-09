import numpy as np
import os

from enthought.traits.api import *
from enthought.traits.ui.api import *
from enthought.traits.ui.menu import *
from enthought.pyface.timer.api import Timer
from enthought.enable.component_editor import ComponentEditor
from enthought.traits.ui.tabular_adapter import TabularAdapter

from enthought.chaco.api import *

import signal_types as signal
import equipment
from widgets import MultiChannelView, DecimatedMultiChannelView, \
        AveragedChannelView

from widgets.tools.window_tool import WindowTool
from pipeline import moving_average, file_sink, add, broadcast
from channel import Channel, MultiChannel, DecimatedMultiChannel, RepeatChannel

class MedusaSettings(HasTraits):

    # IN settings
    attenuation = Range(0.0, 120.0, 20.0)
    ch          = Range(1, 8, 1)
    ch_out_gain = CFloat(10e3)

    fc_low      = CFloat(3e3)
    fc_high     = CFloat(300)

    # OUT settings
    selector    = Instance(signal.SignalSelector, args=())
    signal      = DelegatesTo('selector')
    trial_dur   = CFloat(5)

    sp_lb       = CFloat(5e-5)

    # REPS
    reps        = CInt(-1)

    traits_view = View(
            VGroup(
                Item('sp_lb'),
                Item('attenuation', style='text'),
                Item('ch', label='Channel for OUT-1'),
                Item('ch_out_gain', label='Gain for OUT-1'),
                Item('fc_low', label='Lowpass Cutoff (Hz)'),
                Item('fc_high', label='Highpass Cutoff (Hz)'),
                Item('trial_dur', label='Duration of trial (s)'),
                Item('reps', label='Repetitions (-1=infinite)'),
                Item('selector', editor=InstanceEditor(), style='custom'),
                )
            )

class MedusaController(Controller):
    
    dec_data    = Instance(DecimatedMultiChannel, args=dict(channels=8, window=5))
    raw_data    = Instance(MultiChannel, args=dict(channels=8, window=5))
    sp_data     = Instance(RepeatChannel, args=dict(samples=32, history=5))

    dec_view    = Instance(DecimatedMultiChannelView)
    raw_view    = Instance(MultiChannelView)
    sp_view     = Instance(AveragedChannelView)

    RX6         = Any
    RZ5         = Any
    data_pipe   = Any
    fh          = Any

    num         = Int(0)

    timer       = Instance(Timer)
    settings    = Instance(MedusaSettings, args=())
    running     = Bool(False)

    def _raw_view_default(self):
        self.raw_data.fs = self.RZ5.fs
        view = MultiChannelView(
                value_min=-3e-4,
                value_max=3e-4,
                interactive=False,
                window=6,
                channel=self.raw_data,
                visual_aids=False,
                )
        return view

    def _dec_view_default(self):
        self.dec_data.fs = self.RZ5.fs/10.
        view = DecimatedMultiChannelView(
                value_min=-3e-4,
                value_max=3e-4,
                interactive=False,
                window=6,
                channel=self.dec_data,
                visual_aids=False,
                )
        return view

    def _sp_view_default(self):
        self.sp_data.fs = self.RZ5.fs
        view = AveragedChannelView(
                value_min=-3e-4,
                value_max=3e-4,
                interactive=False,
                window=0.003,
                channel=self.sp_data,
                visual_aids=False,
                )
        view.container.overlays.append(WindowTool(component=view.average_plot))
        return view

    def __init__(self, *args, **kwargs):
        Controller.__init__(self, *args, **kwargs)

        #self.RX6 = equipment.backend.init_device('RepeatPlayRecord', 'RX6')
        self.RZ5 = equipment.backend.init_device('MedusaRecord_v4', 'RZ5')

        self.raw_data.source = self.RZ5.open('mc_sig', 'r', src_type=np.int16,
                dest_type=np.int16, channels=8, sf=8.192e6, read='continuous')
        self.dec_data.source = self.RZ5.open('mc_sig_dec', 'r', src_type=np.int16,
                dest_type=np.int16, channels=8, sf=8.192e6, read='continuous')
        self.sp_data.source = self.RZ5.open('sp', 'r', multiple=32)

        #self.fh = open('100223_sleeping.txt', 'w')
        #f_sink = file_sink(self.fh)

        #self.data_pipe = broadcast([self.dec_data, f_sink])
        self.data_pipe = self.dec_data

        self.timer = Timer(1, self.tick)

    def set(self):
        equipment.backend.set_attenuation(self.settings.attenuation, 'PA5')
        self.settings.signal.fs = self.RX6.fs

        trial_n = self.RX6.sec_to_samples(self.settings.trial_dur)

        self.RX6.set(signal=self.settings.signal, 
                     play_duration=len(self.settings.signal),
                     rec_duration=0,
                     reps=-1,
                     trial_n=trial_n)

        self.RZ5.set(fc_high=self.settings.fc_high,
                     fc_low=self.settings.fc_low,
                     ch=self.settings.ch,
                     ch_out_gain=self.settings.ch_out_gain,
                     sp_lb=self.settings.sp_lb)

    def run(self, info):
        self.set()
        self.RX6.trigger(1)
        self.running = True

    def tick(self):
        #self.fh.write('TRIGGER\n')
        self.data_pipe.send(self.raw_data.source.next())
        #data = self.raw_data.acquire()
        #self.dec_data.acquire()
        self.sp_data.acquire()


plot_size = (300, 300)
view = View(
        HGroup(
            Item('handler.settings', editor=InstanceEditor(), style='custom',
                show_label=False),
            #Item('handler.dec_view.container',
            #    editor=ComponentEditor(size=plot_size), show_label=False,
            #    resizable=True),
            Item('handler.dec_view.container',
                editor=ComponentEditor(size=plot_size), show_label=False,
                resizable=True),
            Item('handler.sp_view.container',
                editor=ComponentEditor(size=plot_size), show_label=False,
                resizable=True),
            ),
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

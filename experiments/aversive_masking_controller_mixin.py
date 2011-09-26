from enthought.traits.api import Instance
from abstract_aversive_controller import AbstractAversiveController

import logging
log = logging.getLogger(__name__)

import neurogen.block_definitions as blocks
from neurogen.sink import Sink

class AversiveMaskingControllerMixin(AbstractAversiveController):

    masker              = Instance(blocks.BandlimitedNoise)
    probe               = Instance(blocks.Tone, ())
    masker_envelope     = Instance(blocks.Block)
    probe_envelope      = Instance(blocks.Block)
    masker_delay        = Instance(blocks.Block)
    probe_delay         = Instance(blocks.Block)
    trial_signal        = Instance(blocks.Block)

    output_trial        = Instance(Sink)
    output_intertrial   = Instance(Sink)

    def _output_trial_default(self):
        return Sink(
                fs=self.iface_behavior.fs,
                token=self.trial_signal.waveform,
                #token=self.masker.waveform,
                calibration=self.cal_primary)

    def _output_intertrial_default(self):
        return Sink(
                fs=self.iface_behavior.fs,
                token=self.masker_envelope.waveform,
                calibration=self.cal_primary)

    def _masker_default(self):
        kwargs = {
                'seed':     1, # -1 = pseudorandom, >0 = frozen
                'order':    1,
                'rp':       2,
                'rs':       60,
                }
        return blocks.BandlimitedNoise(**kwargs)

    def _masker_envelope_default(self):
        return blocks.Cos2Envelope(token=self.masker.waveform, rise_time=0.002)

    def _probe_envelope_default(self):
        return blocks.Cos2Envelope(token=self.probe.waveform, rise_time=0.002)

    def _masker_delay_default(self):
        return blocks.Delay(token=self.masker_envelope.waveform)

    def _probe_delay_default(self):
        return blocks.Delay(token=self.probe_envelope.waveform)

    def _trial_signal_default(self):
        return blocks.Add(
                token_a=self.probe_delay.waveform,
                token_b=self.masker_delay.waveform)

    def set_trial_duration(self, value):
        self.output_intertrial.duration = value
        self.output_trial.duration = value
        self.iface_behavior.cset_tag('trial_dur_n', value, 's', 'n')
        self.iface_behavior.cset_tag('intertrial_n', value, 's', 'n')

        # The intertrial buffer will only report that it has some samples
        # available for writing when the number of samples is greater than the
        # block size.  
        self.buffer_int.block_size = self.iface_behavior.get_tag('trial_dur_n')

    def set_probe_duration(self, value):
        self.probe_envelope.duration = value

    def set_masker_delay(self, value):
        self.masker_delay.delay = value

    def set_probe_delay(self, value):
        self.probe_delay.delay = value

    def set_masker_duration(self, value):
        self.masker_envelope.duration = value

    def set_masker_level(self, value):
        self.masker.level = value
    
    def set_probe_level(self, value):
        self.probe.level = value

    def set_probe_freq(self, value):
        self.probe.frequency = value
        self.masker.fc = value

    def set_masker_level(self, value):
        self.masker.level = value

    def set_masker_bandwidth(self, value):
        self.masker.bandwidth = value

    def update_trial(self):
        att, waveform, clip, floor = self.output_trial.realize()
        self.iface_behavior.set_tag('att_A', att)
        self.buffer_trial.set(waveform)

    def update_intertrial(self):
        import numpy as np
        samples = self.buffer_int.blocks_available()
        blocks = samples/self.buffer_int.block_size
        #waveforms = []
        self.buffer_int.write(np.zeros(samples))
        #for block in range(blocks):
        #    att, waveform = self.output_intertrial.realize()[:2]
        #    waveforms.append(waveform)
        #self.buffer_int.write(np.concatenate(waveforms))

        #print "samples", samples, self.buffer_int.block_size
        #att, waveform = 
        #self.buffer_int.write(waveform)

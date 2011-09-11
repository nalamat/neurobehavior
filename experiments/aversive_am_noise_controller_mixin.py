from enthought.traits.api import Instance, HasTraits
import neurogen.block_definitions as blocks
from neurogen.sink import Sink
import numpy as np

class AversiveAMNoiseControllerMixin(HasTraits):

    int_carrier    = Instance(blocks.Block)
    trial_carrier  = Instance(blocks.Block)
    trial_modulator = Instance(blocks.Block)
    output_int     = Instance(Sink)
    output_trial   = Instance(Sink)

    def _output_int_default(self):
        return Sink(token=self.int_carrier.waveform, fs=self.iface_behavior.fs,
                calibration=self.cal_primary)

    def _output_trial_default(self):
        return Sink(token=self.trial_modulator.waveform,
                fs=self.iface_behavior.fs, calibration=self.cal_primary)

    def set_speaker_equalize(self, value):
        self.output_trial.equalize = value
        self.output_int.equalize = value
    
    def set_level(self, value):
        self.int_carrier.level = value
        self.trial_carrier.level = value

    #def _trial_carrier_default(self):
    #    return blocks.BandlimitedNoise()

    #def _int_carrier_default(self):
    #    return blocks.BandlimitedNoise()

    def _trial_carrier_default(self):
        return blocks.BroadbandNoise()

    def _int_carrier_default(self):
        return blocks.BroadbandNoise()

    def _trial_modulator_default(self):
        return blocks.SAM(token=self.trial_carrier.waveform, 
                equalize_power=True,
                equalize_phase=True)

    #def set_fc(self, value):
    #    self.int_carrier.fc = value
    #    self.trial_carrier.fc = value

    #def set_bandwidth(self, value):
    #    self.int_carrier.bandwidth = value
    #    self.trial_carrier.bandwidth = value
        
    def set_seed(self, value):
        self.int_carrier.seed = value
        self.trial_carrier.seed = value

    def set_modulation_onset(self, value):
        self.trial_modulator.delay = value

    def set_modulation_depth(self, value):
        self.trial_modulator.depth = value

    def set_modulation_direction(self, value):
        self.trial_modulator.direction = value

    def set_trial_duration(self, value):
        super(AversiveAMNoiseControllerMixin, self).set_trial_duration(value)
        self.output_int.duration = value
        self.output_trial.duration = value

    def set_fm(self, value):
        self.trial_modulator.frequency = value

    #def set_rp(self, value):
    #    self.int_carrier.rp = value
    #    self.trial_carrier.rp = value

    #def set_rs(self, value):
    #    self.int_carrier.rs = value
    #    self.trial_carrier.rs = value

    #def set_order(self, value):
    #    self.int_carrier.order = value
    #    self.trial_carrier.order = value

    def update_intertrial(self):
        #offset = self.buffer_int.total_samples_written  
        samples = self.buffer_int.available()
        att, waveform, clip, floor = self.output_int.realize_samples(samples)
        self.iface_behavior.set_tag('att_A', att)
        self.buffer_int.write(waveform)

    def update_trial(self):
        if self.is_warn():
            att, waveform, clip, floor = self.output_trial.realize()
            self.iface_behavior.set_tag('att_A', att)
            self.buffer_trial.set(waveform)

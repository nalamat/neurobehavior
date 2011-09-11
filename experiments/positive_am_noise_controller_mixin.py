from enthought.traits.api import Instance, HasTraits
import neurogen.block_definitions as blocks
from neurogen.sink import Sink
import numpy as np

class PositiveAMNoiseControllerMixin(HasTraits):

    noise_carrier   = Instance(blocks.Block)
    tone_carrier    = Instance(blocks.Block)
    modulator       = Instance(blocks.Block)
    envelope        = Instance(blocks.Block)
    output_primary  = Instance(Sink)
    output_secondary= Instance(Sink)
    
    def set_speaker_equalize(self, value):
        self.output_primary.equalize = value
        self.output_secondary.equalize = value
    
    def set_level(self, value):
        self.noise_carrier.level = value
        self.tone_carrier.level = value
    
    def _tone_carrier_default(self):
        return blocks.Tone(frequency=2e3)

    def _noise_carrier_default(self):
        return blocks.BandlimitedNoise()

    def _envelope_default(self):
        return blocks.Cos2Envelope()

    def set_fc(self, value):
        self.tone_carrier.frequency = value
        self.noise_carrier.fc = value

    def set_bandwidth(self, value):
        if value == 0:
            self.modulator.token = self.tone_carrier.waveform
        else:
            self.modulator.token = self.noise_carrier.waveform
            self.noise_carrier.bandwidth = value
        
    def set_seed(self, value):
        self.noise_carrier.seed = value

    def _modulator_default(self):
        return blocks.SAM(equalize_power=True, equalize_phase=False)

    def _envelope_default(self):
        return blocks.Cos2Envelope(token=self.modulator.waveform)

    def _output_primary_default(self):
        return Sink(token=self.envelope.waveform, fs=self.iface_behavior.fs,
                calibration=self.cal_primary)
    
    def _output_secondary_default(self):
        return Sink(token=self.envelope.waveform, fs=self.iface_behavior.fs,
                calibration=self.cal_secondary)

    def set_modulation_onset(self, value):
        if value == 0:
            self.modulator.equalize_phase = False
        else:
            self.modulator.equalize_phase = True
        self.modulator.delay = value

    def set_rise_fall_time(self, value):
        self.envelope.rise_time = value

    def set_modulation_depth(self, value):
        self.modulator.depth = value

    def set_trial_duration(self, value):
        self.envelope.duration = value
        self.output_primary.duration = value
        self.output_secondary.duration = value
        self.iface_behavior.cset_tag('signal_dur_n', value, 's', 'n')

    def set_fm(self, value):
        self.modulator.frequency = value

    def set_rp(self, value):
        self.noise_carrier.rp = value

    def set_rs(self, value):
        self.noise_carrier.rs = value

    def set_order(self, value):
        self.noise_carrier.order = value

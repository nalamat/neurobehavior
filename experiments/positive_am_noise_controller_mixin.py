from enthought.traits.api import Instance, HasTraits
import neurogen.block_definitions as blocks
from neurogen.sink import Sink
import numpy as np

class PositiveAMNoiseControllerMixin(HasTraits):

    carrier = Instance(blocks.Block)
    modulator = Instance(blocks.Block)
    envelope = Instance(blocks.Block)
    output_primary = Instance(blocks.Block)
    output_secondary = Instance(blocks.Block)
    
    def set_speaker_equalize(self, value):
        self.output_primary.equalize = value
        self.output_secondary.equalize = value
    
    def set_level(self, value):
        self.carrier.level = value
    
    def set_lb_modulation_onset(self, value):
        self.current_lb = value

    def set_ub_modulation_onset(self, value):
        self.current_ub = value
        
    def set_seed(self, value):
        self.carrier.seed = value

    def _carrier_default(self):
        return blocks.BroadbandNoise()

    def _modulator_default(self):
        return blocks.SAM(token=self.carrier.waveform, equalize_power=True,
                          equalize_phase=False)

    def _envelope_default(self):
        return blocks.Cos2Envelope(token=self.modulator.waveform)

    def _output_primary_default(self):
        return Sink(token=self.envelope.waveform, fs=self.iface_behavior.fs,
                    calibration=self.cal_secondary)
    
    def _output_secondary_default(self):
        return Sink(token=self.envelope.waveform, fs=self.iface_behavior.fs,
                    calibration=self.cal_primary)

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

    def set_duration(self, value):
        self.envelope.duration = value
        self.output_primary.duration = value
        self.output_secondary.duration = value
        self.current_duration = value
        self.iface_behavior.cset_tag('signal_dur_n', value, 's', 'n')

    def set_fm(self, value):
        self.modulator.frequency = value

    def set_nogo_parameter(self, value):
        self.current_nogo_parameter = value
        
    def _compute_signal(self):
        self.envelope.duration = self.current_duration
        self.output.duration = self.current_duration
        return self.output.realize()

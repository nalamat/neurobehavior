import numpy as np

from enthought.traits.api import Instance, HasTraits
from neurogen import block_definitions as blocks
from neurogen.sink import Sink

class TemporalIntegrationControllerMixin(HasTraits):

    silence_carrier  = Instance(blocks.Block)
    noise_carrier    = Instance(blocks.Block)
    tone_carrier     = Instance(blocks.Block)
    envelope         = Instance(blocks.Block)
    output_primary   = Instance(Sink)
    output_secondary = Instance(Sink)
    
    def _output_primary_default(self):
        return Sink(token=self.envelope.waveform, fs=self.iface_behavior.fs,
                    calibration=self.cal_primary)
    
    def _output_secondary_default(self):
        return Sink(token=self.envelope.waveform, fs=self.iface_behavior.fs,
                    calibration=self.cal_secondary)
    
    def _silence_carrier(self):
        return blocks.Silence()

    def _tone_carrier_default(self):
        return blocks.Tone(frequency=2e3)

    def _noise_carrier_default(self):
        return blocks.BandlimitedNoise()

    def _envelope_default(self):
        return blocks.Cos2Envelope()

    def set_rise_fall_time(self, value):
        self.envelope.rise_time = value

    def set_fc(self, value):
        # Both cal_primary and cal_secondary should (hopefully) have the same
        # calibrated set of frequencies
        coerced_value = self.cal_primary.get_nearest_frequency(value)
        self.tone_carrier.frequency = coerced_value
        self.noise_carrier.fc = coerced_value
        mesg = 'Coercing {} Hz to nearest calibrated frequency of {} Hz'
        self.notify(mesg.format(value, coerced_value))
        self.set_current_value('fc', coerced_value)

    def set_level(self, value):
        self.tone_carrier.level = value
        self.noise_carrier.level = value

    def set_bandwidth(self, value):
        if value == 0:
            self.envelope.token = self.tone_carrier.waveform
        else:
            self.envelope.token = self.noise_carrier.waveform
            self.noise_carrier.bandwidth = value

    def get_sf(self, attenuation, hw_attenuation):
        delta = hw_attenuation-attenuation
        return 10**(delta/20.0)

    def set_duration(self, value):
        self.envelope.duration = value
        self.output_primary.duration = value
        self.output_secondary.duration = value
        self.iface_behavior.cset_tag('signal_dur_n', value, 's', 'n')
        if self.iface_behavior.get_tag('signal_dur_n') == 0:
            self.iface_behavior.set_tag('signal_dur_n', 1)

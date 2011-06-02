from enthought.traits.api import Instance
from abstract_positive_controller import AbstractPositiveController
from neurogen import block_definitions as blocks
from neurogen.sink import Sink
from neurogen.calibration import Calibration, equalized_data

import numpy as np

import logging
log = logging.getLogger(__name__)

class PositiveDTController(AbstractPositiveController):

    noise_carrier   = Instance(blocks.Block)
    tone_carrier    = Instance(blocks.Block)
    envelope        = Instance(blocks.Block)
    output          = Instance(Sink)

    def _tone_carrier_default(self):
        return blocks.Tone(frequency=2e3)

    def _noise_carrier_default(self):
        return blocks.BandlimitedNoise()

    def _envelope_default(self):
        return blocks.Cos2Envelope()

    def _output_default(self):
        return Sink(token=self.envelope.waveform, fs=self.iface_behavior.fs,
                calibration=Calibration(equalized_data))

    def _compute_signal(self, duration):
        self.envelope.duration = duration
        self.output.duration = duration
        return self.output.realize()

    def set_rise_fall_time(self, value):
        self.envelope.rise_time = value

    def set_fc(self, value):
        self.tone_carrier.frequency = value
        self.noise_carrier.fc = value

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
        self.current_duration = value

    def set_attenuation(self, value):
        self.current_attenuation = value

    def trigger_next(self):
        speaker = self.select_speaker()
        self.current_speaker = speaker

        if self.is_go():
            log.debug("Configuring GO trial")
            self.iface_behavior.set_tag('go?', 1)

            attenuation = self.current_attenuation
            if speaker == 'primary':
                hw_attenuation = self.current_primary_attenuation
            else:
                hw_attenuation = self.current_secondary_attenuation
            sf = self.get_sf(attenuation, hw_attenuation)
            signal = sf*self._compute_signal(self.current_duration)
            self.set_waveform(speaker, signal)
            self.iface_behavior.set_tag('signal_dur_n', len(signal))
        else:
            self.iface_behavior.set_tag('go?', 0)
            self.iface_behavior.set_tag('signal_dur_n', 1)

        # Commence next trial
        self.iface_behavior.trigger(1)

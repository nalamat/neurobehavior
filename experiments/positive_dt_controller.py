from enthought.traits.api import Instance
from abstract_positive_controller import AbstractPositiveController
import neurogen.block_definitions as blocks
import numpy as np

import logging
log = logging.getLogger(__name__)

class PositiveDTController(AbstractPositiveController):

    carrier     = Instance(blocks.Block)
    envelope    = Instance(blocks.Block)
    output      = Instance(blocks.Block)

    def log_trial(self, ts_start, ts_end, last_ttype):
        self.model.data.log_trial(ts_start=ts_start, ts_end=ts_end,
                ttype=last_ttype, speaker=self.current_speaker,
                **self.current_setting_go.parameter_dict())

    def _carrier_default(self):
        return blocks.BandlimitedNoise(seed=-1)

    def _envelope_default(self):
        return blocks.Cos2Envelope(token=self.carrier)

    def _output_default(self):
        return blocks.Output(token=self.envelope)

    def _compute_signal(self, duration):
        self.envelope.duration = duration
        return self.output.realize(self.iface_behavior.fs, duration)

    def set_rise_fall_time(self, value):
        self.envelope.rise_time = value

    def set_fc(self, value):
        self.carrier.fc = value

    def set_bandwidth(self, value):
        self.carrier.bandwidth = value

    def get_sf(self, attenuation):
        delta = self.current_attenuation-attenuation
        return 10**(delta/20.0)

    def set_duration(self, value):
        self.current_duration = value

    def trigger_next(self):
        if self.is_go():
            speaker = self.select_speaker()
            self.set_experiment_parameters(self.current_setting_go)
            self.iface_behavior.set_tag('go?', 1)
            sf = self.get_sf(self.current_setting_go.attenuation)
            signal = sf*self._compute_signal(self.current_duration)
            self.iface_behavior.set_tag('signal_dur_n', len(signal))
        else:
            self.iface_behavior.set_tag('go?', 0)
            self.iface_behavior.set_tag('signal_dur_n', 1)

        # Update settings
        self.set_poke_duration(self.current_poke_dur)

        # Commence next trial
        self.iface_behavior.trigger(1)

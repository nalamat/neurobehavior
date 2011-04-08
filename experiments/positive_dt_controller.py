from enthought.traits.api import Instance
from abstract_positive_controller import AbstractPositiveController
import neurogen.block_definitions as blocks

import logging
log = logging.getLogger(__name__)

class PositiveDTController(AbstractPositiveController):

    carrier     = Instance(blocks.Block)
    envelope    = Instance(blocks.Block)
    output      = Instance(blocks.Block)

    def log_trial(self, ts_start, ts_end, last_ttype):
        print self.current_speaker
        duration = self.current_setting_go.parameter
        attenuation = self.current_setting_go.attenuation
        self.model.data.log_trial(ts_start=ts_start, ts_end=ts_end,
                ttype=last_ttype, duration=duration, attenuation=attenuation,
                speaker=self.current_speaker)

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

    def trigger_next(self):
        if self.current_trial == self.current_num_nogo + 1:
            par = self.current_setting_go.parameter
            self.iface_behavior.set_tag('go?', 1)
            sf = self.get_sf(self.current_setting_go.attenuation)
            waveform = sf*self._compute_signal(par)
            self.buffer_signal.set(waveform)

            self.iface_behavior.set_tag('signal_dur_n', len(waveform))
        else:
            self.iface_behavior.set_tag('go?', 0)

            # TODO: this is a bug!
            #self.buffer_signal.clear()
            # If set to 0, then the signal will play "forever".  Need to look
            # into how to fix this in the rcx file.
            self.iface_behavior.set_tag('signal_dur_n', 1)

        # Update settings
        self.set_poke_duration(self.current_poke_dur)

        # Commence next trial
        self.iface_behavior.trigger(1)

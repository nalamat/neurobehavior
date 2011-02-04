from abstract_positive_controller import AbstractPositiveController
import neurogen.block_definitions as blocks

import logging
log = logging.getLogger(__name__)

class PositiveDTController(AbstractPositiveController):

    def log_trial(self, ts_start, ts_end, last_ttype):
        parameter = self.current_setting_go.parameter
        attenuation = self.current_setting_go.attenuation
        self.model.data.log_trial(ts_start, ts_end, last_ttype, 
                (parameter, attenuation))

    def _compute_signal(self, duration):
        carrier = blocks.BroadbandNoise(seed=-1)
        envelope = blocks.Cos2Envelope(rise_time=self.current_rise_fall_time,
                                       duration=duration, token=carrier)
        output = blocks.Output(token=envelope)
        return output.realize(self.iface_behavior.fs, duration)

    def set_attenuation(self, value):
        self.iface_behavior.set_tag('att_A', value)

    def trigger_next(self):
        if self.current_trial == self.current_num_nogo + 1:
            par = self.current_setting_go.parameter
            self.iface_behavior.set_tag('go?', 1)
            waveform = self._compute_signal(par)
            self.buffer_signal.set(waveform)
            self.set_attenuation(self.current_setting_go.attenuation)
            self.iface_behavior.set_tag('signal_dur_n', len(waveform))
        else:
            self.iface_behavior.set_tag('go?', 0)
            self.set_attenuation(120)
            self.buffer_signal.clear()
            # If set to 0, then the signal will play "forever".  Need to look
            # into how to fix this in the rcx file.
            self.iface_behavior.set_tag('signal_dur_n', 1)

        # Update settings
        self.set_poke_duration(self.current_poke_dur)

        # Commence next trial
        self.iface_behavior.trigger(1)

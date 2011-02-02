from abstract_positive_controller import AbstractPositiveController
import neurogen.block_definitions as blocks

import logging
log = logging.getLogger(__name__)

class PositiveDTController(AbstractPositiveController):

    def log_trial(self, ts_start, ts_end, last_ttype):
        parameter = self.current_setting_go.parameter
        attenuation = self.current_setting_go.attenuation
        self.model.data.log_trial(ts_start, ts_end, last_ttype, parameter,
                attenuation)

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
        else:
            par = self.current_nogo_parameter
            self.iface_behavior.set_tag('go?', 0)

        # Prepare next signal
        waveform = self._compute_signal(par)
        self.buffer_signal.set(waveform)
        self.set_attenuation(self.current_setting_go.attenuation)
        self.iface_behavior.set_tag('signal_dur_n', len(waveform))

        # Prepare next reward
        self.set_poke_duration(self.current_poke_dur)
        self.set_reward_duration(self.current_setting_go.reward_duration)
        self.iface_pump.rate = self.current_setting_go.reward_rate

        # Commence next trial
        self.iface_behavior.trigger(1)

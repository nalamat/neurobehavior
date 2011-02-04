from abstract_positive_controller import AbstractPositiveController
import neurogen.block_definitions as blocks

class PositiveAMNoiseController(AbstractPositiveController):

    def _compute_signal(self, depth):
        carrier = blocks.BroadbandNoise(seed=-1)
        modulator = blocks.SAM(token=carrier, 
                               depth=depth,
                               equalize_power=True,
                               equalize_phase=False,
                               frequency=self.current_fm)
        envelope = blocks.Cos2Envelope(token=modulator,
                                       rise_time=self.current_rise_fall_time,
                                       duration=self.current_duration)
        output = blocks.Output(token=envelope)
        return output.realize(self.iface_behavior.fs, self.current_duration)

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
        self.set_attenuation(self.current_attenuation)
        self.iface_behavior.set_tag('signal_dur_n', len(waveform))

        self.set_poke_duration(self.current_poke_dur)

        self.iface_behavior.trigger(1)

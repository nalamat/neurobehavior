from enthought.traits.api import Any

from abstract_positive_controller import AbstractPositiveController
import neurogen.block_definitions as blocks

class PositiveAMNoiseController(AbstractPositiveController):

    # The blocks that create the signal
    carrier     = Any
    modulator   = Any
    envelope    = Any
    output      = Any

    def set_seed(self, value):
        self.carrier.seed = value

    def _carrier_default(self):
        return blocks.BroadbandNoise()

    def _modulator_default(self):
        return blocks.SAM(token=self.carrier, 
                          equalize_power=True,
                          equalize_phase=False)

    def _envelope_default(self):
        return blocks.Cos2Envelope(token=self.modulator)

    def _output_default(self):
        return blocks.Output(token=self.envelope)

    def _compute_signal(self, parameter):
        self.modulator.depth = parameter
        return self.output.realize(self.buffer_signal.fs,
                                   self.current_duration)

    def set_rise_fall_time(self, value):
        self.envelope.rise_time = value

    def set_duration(self, value):
        self.envelope.duration = value
        self.current_duration = value

    def set_fm(self, value):
        self.modulator.frequency = value

    def set_nogo_parameter(self, value):
        self.current_nogo_parameter = value

    def trigger_next(self):
        if self.current_trial == self.current_num_nogo + 1:
            par = self.current_setting_go.parameter
            self.iface_behavior.set_tag('go?', 1)
        else:
            par = self.current_nogo_parameter
            self.iface_behavior.set_tag('go?', 0)

        # Prepare next signal
        waveform = self._compute_signal(par)
        #self.buffer_signal.set(waveform)
        self.iface_behavior.set_tag('signal_dur_n', len(waveform))
        self.set_poke_duration(self.current_poke_dur)
        self.iface_behavior.trigger(1)

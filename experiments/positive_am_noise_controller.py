from enthought.traits.api import Any
from numpy.random import uniform
from abstract_positive_controller import AbstractPositiveController
import neurogen.block_definitions as blocks

class PositiveAMNoiseController(AbstractPositiveController):

    # The blocks that create the signal
    carrier     = Any
    modulator   = Any
    envelope    = Any
    output      = Any

    def set_lb_modulation_onset(self, value):
        self.current_lb = value

    def set_ub_modulation_onset(self, value):
        self.current_ub = value
        
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

    def _compute_signal(self):
        return self.output.realize(self.buffer_out1.fs, self.current_duration)

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
        self.current_duration = value

    def set_fm(self, value):
        self.modulator.frequency = value

    def set_nogo_parameter(self, value):
        self.current_nogo_parameter = value

    def trigger_next(self):
        speaker = self.select_speaker()
        self.current_speaker = speaker

        if self.is_go():
            self.set_experiment_parameters(self.current_setting_go)
            self.iface_behavior.set_tag('go?', 1)
        else:
            self.set_experiment_parameters(self.current_nogo)
            self.iface_behavior.set_tag('go?', 0)

        # Prepare next signal
        waveform = self._compute_signal()
        self.set_waveform(speaker, waveform)
        #self.buffer_out1.set(waveform)
        self.iface_behavior.set_tag('signal_dur_n', len(waveform))
        self.iface_behavior.trigger(1)

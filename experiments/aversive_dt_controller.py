from neurogen import block_definitions as blocks

from enthought.traits.api import Any
from abstract_aversive_controller import AbstractAversiveController

from os.path import join

class AversiveDTController(AbstractAversiveController):

    output      = Any
    carrier     = Any
    envelope    = Any

    def compute_waveform(self):
        return self.output.realize(self.iface_behavior.fs,
                self.current_trial_duration)

    def _carrier_default(self):
        return blocks.Tone()

    def _envelope_default(self):
        return blocks.Cos2Envelope(token=self.carrier)

    def _output_default(self):
        return blocks.Output(token=self.envelope)

    # We are overriding the three signal update methods (remind, warn, safe) to
    # work with the specific circuit we constructed
    def update_remind(self):
        self.set_experiment_parameters(self.current_remind)
        self.buffer_trial.set(self.compute_waveform())

    def update_warn(self):
        self.set_experiment_parameters(self.current_warn)
        self.buffer_trial.set(self.compute_waveform())

    def update_safe(self):
        #self.buffer_int.clear()
        pass

    def set_frequency(self, value):
        self.carrier.frequency = value

    def set_ramp_duration(self, value):
        self.envelope.ramp_duration = value

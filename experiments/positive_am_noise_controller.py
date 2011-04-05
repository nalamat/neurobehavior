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

    def _compute_signal(self, parameter):
        self.modulator.depth = parameter
        return self.output.realize(self.buffer_signal.fs,
                                   self.current_duration)

    def set_delay(self, value):
        if value == 0:
            self.modulator.equalize_phase = False
        else:
            self.modulator.equalize_phase = True
        self.modulator.delay = value

    def set_rise_fall_time(self, value):
        self.envelope.rise_time = value

    def set_duration(self, value):
        self.envelope.duration = value
        self.current_duration = value

    def set_fm(self, value):
        self.modulator.frequency = value

    def set_nogo_parameter(self, value):
        self.current_nogo_parameter = value

    def _recompute_delay(self):
        # Draw a single value from the range [current_lb, current_ub)
        onset = uniform(self.current_lb, self.current_ub, 1)[0]
        # The logic for setting the modulation onset is defined in set_delay
        self.set_delay(onset)
        self.current_onset = onset
        self.set_reaction_window_delay(onset)
        
        # We need to update the reaction_window_duration as well because it
        # is implemented as the sum of the delay and duration in the RPvds
        # circuit (this is really a poorly-named variable since the RPvds
        # wants the start time and end time of the reaction window, not the
        # delay and duration values).
        self.set_reaction_window_duration(self.current_reaction_window_duration)

    def trigger_next(self):
        self._recompute_delay()

        if self.is_go():
            # Next trial should be a GO trial
            par = self.current_setting_go.parameter
            self.iface_behavior.set_tag('go?', 1)
        else:
            # Next trial should be a NOGO trial
            par = self.current_nogo_parameter
            self.iface_behavior.set_tag('go?', 0)

        self.update_attenuation()

        # Prepare next signal
        waveform = self._compute_signal(par)
        # Upload signal to hardware
        self.buffer_signal.set(waveform)
        self.iface_behavior.set_tag('signal_dur_n', len(waveform))
        # Set poke duration for next trial
        self.set_poke_duration(self.current_poke_dur)
        self.iface_behavior.trigger(1)

    def log_trial(self, ts_start, ts_end, last_ttype):
        if self.is_go():
            parameter = self.current_setting_go.parameter
        else:
            parameter = self.current_nogo_parameter
        onset = self.current_onset
        if onset is None:
            onset = 0
        self.model.data.log_trial(ts_start, ts_end, last_ttype, parameter,
                onset)

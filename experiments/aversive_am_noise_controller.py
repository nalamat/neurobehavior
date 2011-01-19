from enthought.traits.api import Any
from neurogen import block_definitions as blocks
from abstract_aversive_controller import AbstractAversiveController

from numpy.random import randint

import logging
log = logging.getLogger(__name__)

class AversiveAMNoiseController(AbstractAversiveController):

    current_signal = Any

    def _current_signal_default(self):
        signal = blocks.SAM(
                token=blocks.BroadbandNoise(seed=-1),
                fm=self.current_modulation_frequency, 
                equalize_power=True,
                equalize_phase=True,
                depth=0)
        return blocks.SimpleWaveform(token=signal)

    def _compute_signal(self, depth):
        direction = 'positive' if randint(0, 2) else 'negative'
        self.current_signal.token.depth = depth
        self.current_signal.token.equalize_direction = direction
        fs = self.iface_behavior.fs
        duration = self.current_trial_duration
        return self.current_signal.realize(fs, duration)

    def set_attenuation(self, value):
        self.iface_behavior.set_tag('att_A', value)

    def update_remind(self):
        waveform = self._compute_signal(self.current_remind.parameter)
        self.buffer_trial.set(waveform)

    def update_warn(self):
        waveform = self._compute_signal(self.current_warn.parameter)
        self.buffer_trial.set(waveform)

    def update_safe(self):
        self.set_attenuation(self.current_attenuation)
        if self.buffer_int.written == 0:
            # We have not yet initialized the buffer with data.  Let's fill it
            # all up in one shot.
            self.current_signal.token.depth = self.current_safe.parameter

            # Let's freeze our safe signal and turn it into a generator.  This
            # will allow us to grab the next set of samples from the signal
            # without having to worry about tracking requisite things like
            # offset.
            fs = self.iface_behavior.fs
            self.buffer_safe = self.current_signal.freeze(fs)
            samples = int(fs*self.current_trial_duration)
            waveform = self.buffer_safe.send(samples)
            self.buffer_int.set(waveform)
            self.buffer_int.block_size = int(samples/2.0)
        else:
            # We need to incrementially update as needed.  Note that we are now
            # reading from our "frozen" signal
            pending = self.buffer_int.pending()
            if pending > 0:
                waveform = self.buffer_safe.send(pending)
                self.buffer_int.write(waveform)

from ..signal import Signal
import numpy as np

class Noise(Signal):

    def _get_signal(self):
        noise = np.random.uniform(low=-1, high=1, size=len(self.t))
        return self.amplitude*noise

    def _get_period(self):
        return 0

    def _get_coerced_duration(self):
        return self.duration

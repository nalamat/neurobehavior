from .noise import Noise
from .envelope_mixin import AMMixin

class AMNoise(Noise, AMMixin):

    def _get_signal(self):
        signal = Noise._get_signal(self)
        return self.envelope*signal

    def _get_period(self):
        return self.envelope_period

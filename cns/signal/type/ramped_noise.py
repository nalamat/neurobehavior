from .noise import Noise
from .envelope_mixin import RampMixin

class RampedNoise(Noise, RampMixin):

    def _get_signal(self):
        return Noise._get_signal(self)*self.envelope

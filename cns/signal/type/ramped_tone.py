from .tone import Tone
from .envelope_mixin import RampMixin

class RampedTone(Tone, RampMixin):

    def compute_waveform(self, t):
        signal = Tone.compute_waveform(self, t)
        return signal * self.envelope

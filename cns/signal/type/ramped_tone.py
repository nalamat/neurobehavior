from .tone import Tone
from .envelope_mixin import RampMixin

class RampedTone(Tone, RampMixin):

    def _get_signal(self):
        return Tone._get_signal(self)*self.envelope

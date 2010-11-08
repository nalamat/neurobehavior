from .tone import Tone
from .envelope_mixin import AMMixin

class AMTone(Tone, AMMixin):

    def _get_signal(self):
        signal = Tone._get_signal(self)
        return self.envelope * signal

    def _get_period(self):
        return self.env_period

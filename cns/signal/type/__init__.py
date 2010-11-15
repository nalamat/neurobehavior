from .silence import Silence
from .tone import Tone
from .fm_tone import FMTone
from .noise import Noise
from .am_noise import AMNoise
from .am_tone import AMTone
from .ramped_tone import RampedTone
from .ramped_noise import RampedNoise
from .bandlimited_noise import BandlimitedNoise
from .delayed_am_noise import DelayedAMNoise

signal_types = {
        Silence     : 'silence',
        Tone        : 'tone',
        FMTone      : 'FM tone',
        Noise       : 'noise',
        AMNoise     : 'AM noise',
        AMTone      : 'AM tone',
        RampedTone  : 'ramped tone',
        RampedNoise : 'ramped noise',
        BandlimitedNoise : 'band-limited noise',
        DelayedAMNoise : 'delayed AM noise',
        }

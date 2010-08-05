from .silence import Silence
from .tone import Tone
from .fm_tone import FMTone
from .noise import Noise
from .am_noise import AMNoise
from .am_tone import AMTone
from .ramped_tone import RampedTone

signal_types = {
        Silence     : 'silence',
        Tone        : 'tone',
        FMTone      : 'FM tone',
        Noise       : 'noise',
        AMNoise     : 'AM noise',
        AMTone      : 'AM tone',
        RampedTone  : 'ramped tone',
        }

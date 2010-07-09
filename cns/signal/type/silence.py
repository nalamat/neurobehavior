from enthought.traits.api import Constant
from ..signal import Signal
import numpy as np

class Silence(Signal):

    level = Constant(0, configurable=False, 
                     label='Level', unit='dB SPL',
                     store='attribute')

    def _get_signal(self):
        return np.zeros(len(self.t))

    def _get_period(self):
        return 0

    def _get_coerced_duration(self):
        return self.duration

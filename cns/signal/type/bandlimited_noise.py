from ..signal import Signal
import numpy as np
from scipy.signal import iirfilter, filtfilt

from enthought.traits.api import Float

class BandlimitedNoise(Signal):

    center_frequency = Float(5000, configurable=True, label='Center frequency',
            unit='Hz', store='attribute')
    bandwidth = Float(2500, configurable=True, label='Bandwidth', unit='Hz',
            store='attribute')

    def _get_signal(self):
        noise = np.random.uniform(low=-1, high=1, size=len(self.t))
        fl = self.center_frequency-self.bandwidth
        fh = self.center_frequency+self.bandwidth
        Wn = np.divide([fl, fh], self.fs/2)
        b, a = iirfilter(8, Wn)
        return filtfilt(b, a, self.amplitude*noise)

    def _get_period(self):
        return 0

    def _get_coerced_duration(self):
        return self.duration

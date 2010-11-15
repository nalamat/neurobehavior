from .noise import Noise
from .envelope_mixin import AMMixin

from enthought.traits.api import Float
import numpy as np

class DelayedAMNoise(Noise, AMMixin):

    am_delay = Float(0.1, configurable=True, label='AM delay', unit='seconds',
            store='attribute')

    def _get_signal(self):
        signal = Noise._get_signal(self)
        env = self.envelope
        unmodulated = np.ones(self.am_delay*self.fs)
        env = np.r_[unmodulated, env][:-len(unmodulated)]
        return env*signal

    def _get_period(self):
        return self.envelope_period

if __name__ == '__main__':
    noise = DelayedAMNoise(fs=10e3, env_depth=0.5)
    from pylab import *
    plot(noise.signal); show();

    noise = DelayedAMNoise(fs=10e3, env_depth=0.25)
    #from pylab import *
    plot(noise.signal); show();

    noise = DelayedAMNoise(fs=10e3, env_depth=0)
    #from pylab import *
    plot(noise.signal); show();

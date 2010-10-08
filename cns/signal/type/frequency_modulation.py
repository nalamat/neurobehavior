from enthought.traits.api import CFloat
from ..signal import Signal
import numpy as np
from cns.util.math import lcm

class FMTone(Signal):

    fc =            CFloat(500, configurable=True,
                           label='Carrier frequency', unit='Hz',
                           store='attribute')
    fm =            CFloat(5, configurable=True,
                           label='Modulation frequency', unit='Hz',
                           store='attribute')
    beta =          CFloat(1, configurable=True,
                           label='Modulation index', unit=None,
                           store='attribute')

    # General FM equation
    # carrier x_c(t) = X_c*cos(\omega_c t)
    # modulator x_m(t) = \beta*sin(\omega_m t)
    # x(t) = X_c*cos[\omega_c t + \beta*sin(\omega_m t)]
    # \beta = (\delta\omega)/\omega_m)
    # i.e. maximum carrier frequency deviation/modulation frequency

    def _get_signal(self):
        #beta = self.delta_fc_max/self.fm
        modulator = self.beta*np.cos(2*np.pi*self.fm*self.t)
        return self.amplitude*np.sin(2*np.pi*self.fc*self.t-modulator)

    def _get_period(self):
        import decimal
        # We have to convert the periods of fm and fc to a Decimal for the
        # least common multiple calculation otherwise binary floating point
        # issues may pop up (e.g. 1.00 % 0.1 returns 0.09999999999995) resulting
        # in arbitrarily long periods.
        l_fm = decimal.Decimal(str(self.fm**-1))
        l_fc = decimal.Decimal(str(self.fc**-1))
        return float(lcm(l_fm, l_fc))

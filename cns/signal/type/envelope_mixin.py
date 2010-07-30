from enthought.traits.api import HasTraits, Property, CFloat, Range, Enum, \
        Bool, on_trait_change
import logging
log = logging.getLogger(__name__)

import numpy as np

class EnvelopeMixin(HasTraits):

    envelope = Property

class AMMixin(EnvelopeMixin):

    env_fm              = CFloat(5, configurable=True,
                                 label='Modulation frequency', unit='Hz',
                                 store='attribute')

    env_depth           = Range(0.0, 1.0, 1.0, configurable=True,
                                label='Modulation depth', unit='Fraction',
                                store='attribute')

    env_period          = Property

    power_corr          = Property
    phase_corr          = Property
    

    power_correction    = Bool(True, configurable=True,
                               label='Correct for average power',
                               unit=None,
                               store='attribute')

    phase_correction    = Bool(True, configurable=True,
                               label='Correct for phase',
                               unit=None,
                               store='attribute')

    def _get_power_corr(self):
        if self.power_correction:
            return (3/8.*self.env_depth**2-self.env_depth+1)**0.5
        else:
            return 1

    def _get_phase_corr(self):
        if self.phase_correction:
            z = 2/self.env_depth*self.power_corr-2/self.env_depth+1
            return np.arccos(z)
        else:
            return 0
    
    def _get_env_period(self):
        return self.env_fm ** -1

    def _get_envelope(self):
        env = 0.5 * np.sin(self.t*2*np.pi*self.env_fm+self.phase_corr) + 0.5
        env *= self.env_depth
        env += 1 - self.env_depth
        env *= 1/self.power_corr
        return env

class RampMixin(EnvelopeMixin):

    ramp_type       = Enum('cosine squared', 'cosine', 'linear',
                           label='Ramp type', unit=None,
                           store='attribute')
    ramp_time       = CFloat(0.5e-3, configurable=True,
                             label='Ramp time', unit='sec',
                             store='attribute')
    ramp_delay      = CFloat(0, configurable=True,
                             label='Ramp onset delay', unit='sec',
                             store='attribute')
    ramp_duration   = CFloat(0.512, configurable=True,
                             label='Envelope duration', unit='sec',
                             store='attribute')
    ramp_delay_ref  = Enum('onset', 'offset', configurable=True,
                           label='Delay from', unit=None,
                           store='attribute')

    @on_trait_change('ramp_duration, ramp_delay, ramp_time')
    def check_ramp_duration(self, trait, new):
        max_ramp = self.duration-(2*self.ramp_time+self.ramp_delay)
        if self.ramp_duration > max_ramp:
            log.warn('Requested ramp duration %r for %r is too long',
                    self.ramp_duration, self)
            log.warn('Coercing ramp duration for %r to %r', self, max_ramp)
            self.set(trait_change_notify=False, ramp_duration=max_ramp)

    def generate_ramp(self):
        n = int(self.ramp_time * self.fs)

        if self.ramp_type == 'cosine squared':
            return np.sin(np.linspace(0, np.pi / 2., n)) ** 2
        elif self.ramp_type == 'cosine':
            return np.sin(np.linspace(0, np.pi / 2., n))
        elif self.ramp_type == 'linear':
            return np.arange(n, dtype='f') / n

    def _get_envelope(self):
        ramp = self.generate_ramp()
        n = int(self.ramp_duration * self.fs) - len(ramp)
        envelope = np.r_[ramp, np.ones(n), ramp[::-1]]

        if self.ramp_delay_ref == 'onset':
            pre_n = int(self.ramp_delay * self.fs)
            post_n = len(self.t) - len(envelope) - pre_n
        else:
            post_n = int(self.ramp_delay * self.fs)
            pre_n = len(self.t) - len(envelope) - post_n

        return np.r_[np.zeros(pre_n), envelope, np.zeros(post_n)]

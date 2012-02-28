from traits.api import HasTraits, Any
import numpy as np
from cns import signal as wave

import logging
log = logging.getLogger(__name__)

class PositiveDTControllerMixin(HasTraits):

    #########################################################################
    # Fixed attenuation logic
    #########################################################################

    def set_expected_speaker_range(self, value):
        self._update_attenuators()

    def set_fixed_attenuation(self, value):
        self._update_attenuators()

    def _update_attenuators(self):
        if self.get_current_value('fixed_attenuation'):
            ranges = self.get_current_value('expected_speaker_range')
            ranges = [(s.frequency, s.max_level) for s in ranges]
            att1 = self.cal_primary.get_best_attenuation(ranges)
            att2 = self.cal_secondary.get_best_attenuation(ranges)
            log.debug('Best attenuations are %.2f and %.2f', att1, att2)
            self.set_attenuations(att1, att2, False)

    #########################################################################
    # Cached waveforms to speed up computation
    #########################################################################

    _time = Any
    _token = Any
    _envelope = Any

    #########################################################################
    # Trigger recomputation of cached time/token/envelope as needed
    #########################################################################

    def set_rise_fall_time(self, value):
        self._recompute_envelope()

    def set_fc(self, value):
        # Both cal_primary and cal_secondary should (hopefully) have the same
        # calibrated set of frequencies
        coerced_value = self.cal_primary.get_nearest_frequency(value)
        self.set_current_value('fc', coerced_value)
        mesg = 'Coercing {} Hz to nearest calibrated frequency of {} Hz'
        self.notify(mesg.format(value, coerced_value))
        self._recompute_token()

    def set_duration(self, value):
        self.iface_behavior.cset_tag('signal_dur_n', value, 's', 'n')
        if self.iface_behavior.get_tag('signal_dur_n') == 0:
            self.iface_behavior.set_tag('signal_dur_n', 1)
        self._recompute_time()
        self._recompute_token()
        self._recompute_envelope()

    #########################################################################
    # Methods for computing/caching waveform
    #########################################################################

    def _recompute_time(self):
        duration = self.get_current_value('duration')
        self._time = wave.time(self.buffer_out.fs, duration)

    def _recompute_token(self):
        fc = self.get_current_value('fc')
        self._token = np.sin(2*np.pi*fc*self._time)

    def _recompute_envelope(self):
        rise_time = self.get_current_value('rise_fall_time')
        ramp_n = int(rise_time*self.buffer_out.fs)
        self._envelope = wave.generate_envelope(len(self._time), ramp_n)

    def compute_waveform(self):
        waveform = self._token * self._envelope
        # LOGIC TO HANDLE ATTENUATION/SCALING

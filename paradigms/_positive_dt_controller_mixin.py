import numpy as np
from traits.api import HasTraits, Bool, Property, Any
from cns import signal as wave
from cns import get_config

MAX_VRMS = get_config('MAX_SPEAKER_DAC_VOLTAGE')

import logging
log = logging.getLogger(__name__)

class PositiveDTControllerMixin(HasTraits):
    
    # This paradigm demonstrates how one can cache some of the computations
    # underlying the waveform generation.  Essentially we cache the "pieces" of
    # the waveform (e.g. the token and envelope) and load the cached waveform
    # each time we need to generate and upload the trial token.

    #########################################################################
    # Fixed attenuation logic
    #########################################################################

    # This will *only* be called when the user updates the
    # expected_speaker_range list via the GUI and hits the "apply" button.  We
    # want to ensure that the waveform can be scaled up to 7 volts peak-to-peak.
    def set_expected_speaker_range(self, value):
        att1 = self.cal_primary.get_best_attenuation(value, voltage=MAX_VRMS)
        att2 = self.cal_secondary.get_best_attenuation(value, voltage=MAX_VRMS)
        log.debug('Best attenuations are %.2f and %.2f', att1, att2)
        self.set_attenuations(att1, att2)

    #########################################################################
    # Cached waveforms to speed up computation
    #########################################################################

    _time = Any
    _token = Any
    _envelope = Any

    def _get_time(self):
        if not self._time_valid:
            log.debug('recomputing _time')
            duration = self.get_current_value('duration')
            self._time = wave.time(self.buffer_out.fs, duration)
            self._time_valid = True
        return self._time

    def _get_token(self):
        if not self._token_valid:
            log.debug('recomputing _token')
            fc = self.get_current_value('fc')
            t = self._get_time()
            self._token = np.sin(2*np.pi*fc*t)
            self._token_valid = True
        return self._token

    def _get_envelope(self):
        if not self._envelope_valid:
            log.debug('recomputing _envelope')
            rise_time = self.get_current_value('rise_fall_time')
            ramp_n = int(rise_time*self.buffer_out.fs)
            t = self._get_time()
            self._envelope = wave.generate_envelope(len(t), ramp_n)
            self._envelope_valid = True
        return self._envelope

    #########################################################################
    # Boolean flags indicating whether or not cached data is valid
    #########################################################################

    _time_valid = Bool(False)
    _token_valid = Bool(False)
    _envelope_valid = Bool(False)

    # All HasTraits classes will call the function _<attribute_name>_changed
    # whenever the value of the attribute changes.  If the function does not
    # exist, nothing is done.  Note the double underscore in the function
    # definition due to the fact that the attribute name, _time_valid, starts
    # with a single underscore.
    def __time_valid_changed(self, value):
        if not value:
            log.debug('_time is invalid, invalidating _token and _envelope')
            self._token_valid = False
            self._envelope_valid = False

    #########################################################################
    # Trigger recomputation of cached time/token/envelope as needed
    #########################################################################

    def set_rise_fall_time(self, value):
        self._envelope_valid = False

    def set_fc(self, value):
        # Both cal_primary and cal_secondary should (hopefully) have the same
        # calibrated set of frequencies
        coerced_value = self.cal_primary.get_nearest_frequency(value)
        self.set_current_value('fc', coerced_value)

        # Let's let the user know, just in case this is something they care
        # about.
        mesg = 'Coercing {} Hz to nearest calibrated frequency of {} Hz'
        self.notify(mesg.format(value, coerced_value))

        # Currently the logic which calls the set_<parameter_name> functions
        # checks to see what value the user has specified for the parameter.  In
        # this case, the following steps occur:
        # * The user has specified 12000 Hz as the arrier frequency via the GUI
        # * self.set_fc(12000) is executed and the value gets coerced to 12007
        # * On the next trial, the requested value is (still) 12000 because
        #   that's what was requested via the GUI.  This value is compared with
        #   the value of the previous trial, which was coerced to 12007.  Since
        #   12007 != 12000, it looks like the value has changed so
        #   self.set_fc(12000) is called.
        # * self.set_fc(12000) coerces the value to 12007.  Since the carrier
        #   frequency used for computing the waveform hasn't changed, there's no
        #   need to mark the token as invalid.  But, we need to check that this
        #   is, indeed, the case by calling self.value_changed('fc') after we
        #   update the current value via self.set_current_value('fc', 12007).
        if self.value_changed('fc'):
            # Yup! The value has changed even after we coerced it to the nearest
            # calibrated frequency.
            self._token_valid = False
        else:
            # Despite the fact that self.set_fc was called as if the carrier
            # frequency has changed, we have coerced the value to the nearest
            # frequency and it turns out the carrier frequency we use for
            # computing the token has not changed.  Therefore, nothing needs to
            # be done.
            pass

    def set_duration(self, value):
        self.iface_behavior.cset_tag('signal_dur_n', value, 's', 'n')
        if self.iface_behavior.get_tag('signal_dur_n') == 0:
            self.iface_behavior.set_tag('signal_dur_n', 1)

        # Note that as soon as we set self._time_valid to False,
        # self.__time_valid_changed(False) will be executed which sets
        # self._token_valid and self._envelope_valid to False.  This is an
        # Enthought Traits feature.
        self._time_valid = False

    #########################################################################
    # Methods for computing/caching waveform
    #########################################################################

    def compute_waveform(self, calibration, hw_attenuation):
        # We could also cache the waveform as well since it will not change if
        # we are only roving level.
        waveform = self._get_token() * self._get_envelope()
        
        # Given the calibration file and hardware attenuation (which we do not
        # wish to change), compute the appropriate scaling factor for the
        # waveform.
        fc = self.get_current_value('fc')
        level = self.get_current_value('level')
        sf = calibration.get_sf(fc, level, hw_attenuation, voltage=1, gain=0)
        log.debug('Scaling factor is %f', sf)

        # Scale the waveform and return None (because we already handle setting
        # the hardware attenuation via the self.set_expected_speaker_range
        # method (defined in this file).
        return sf*waveform, None

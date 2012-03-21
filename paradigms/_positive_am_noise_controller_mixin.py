from traits.api import HasTraits, Any, Bool

# For generating the signal
from cns import signal as wave
import numpy as np
from scipy import signal
from cns import get_config
import time

MAX_VRMS = get_config('MAX_SPEAKER_DAC_VOLTAGE')

import logging
log = logging.getLogger(__name__)

class PositiveAMNoiseControllerMixin(HasTraits):

    #########################################################################
    # Cached data to speed up computation
    #########################################################################

    _time = Any
    _cos_envelope = Any
    _sam_envelope = Any
    _noise_token = Any
    _filtered_noise_token = Any
    _sw_att1 = Any
    _sw_att2 = Any

    #########################################################################
    # Boolean flags indicating whether or not cached data is valid
    #########################################################################

    _time_valid = Bool(False)
    _cos_envelope_valid = Bool(False)
    _sam_envelope_valid = Bool(False)
    _noise_token_valid = Bool(False)
    _filtered_noise_token_valid = Bool(False)

    # Be sure that changes to arrays cascade to other arrays that depend on the
    # modified array
    def __time_valid_changed(self, value):
        if not value:
            log.debug('Marking envelopes and noise token as invalid')
            self._cos_envelope_valid = False
            self._sam_envelope_valid = False
            self._noise_token_valid = False

    def __noise_token_valid_changed(self, value):
        if not value:
            log.debug('Marking filtered noise token as invalid')
            self._filtered_noise_token_valid = False

    ########################################################################
    # Trigger recomputation of cosine envelope when rise time changes
    ########################################################################

    def set_rise_fall_time(self, value):
        self._cos_envelope_valid = False

    ########################################################################
    # Recompute SAM envelope when modulation changes
    ########################################################################

    def set_fm(self, value):
        self._sam_envelope_valid = False

    def set_modulation_depth(self, value):
        self._sam_envelope_valid = False
        
    def set_modulation_direction(self, value):
        self._sam_envelope_valid = False

    def set_modulation_onset(self, value):
        self._sam_envelope_valid = False

    ########################################################################
    # Recompute base noise token when seed changes
    ########################################################################

    def set_seed(self, value):
        self._noise_token_valid = False

    ########################################################################
    # Recompute filter noise token when filter settings change
    ########################################################################

    def set_rp(self, value):
        self._filtered_noise_token_valid = False

    def set_rs(self, value):
        self._filtered_noise_token_valid = False

    def set_order(self, value):
        self._filtered_noise_token_valid = False

    def set_bandwidth(self, value):
        self._filtered_noise_token_valid = False

    ########################################################################
    # Center frequency affects both the filtered token and the attenuation
    ########################################################################

    def set_fc(self, value):
        self._filtered_noise_token_valid = False

    ########################################################################
    # Methods for computing/caching waveform
    ########################################################################

    def _get_time(self):
        if not self._time_valid:
            log.debug('recomputing time')
            duration = self.get_current_value('duration')
            self._time = wave.time(self.iface_behavior.fs, duration)
            self._time_valid = True
        return self._time
        
    def _get_noise_token(self):
        # Compute the noise waveform (using the seed)
        if not self._noise_token_valid:
            log.debug('recomputing noise token')
            seed = self.get_current_value('seed')
            if seed < 0:
                # If seed is -1, this means the user wants a random seed.  Use the
                # system clock to get a random integer.
                seed = int(time.time())

            state = np.random.RandomState(seed)
            t = self._get_time()
            token = state.uniform(low=-1, high=1, size=len(t))
            self._noise_token = token
            self._noise_token_valid = True
        return self._noise_token

    def _get_filtered_noise_token(self):
        # Compute the filtered waveform using the cached noise waveform.  Note
        # that we do this caching because computing filter coefficients can be a
        # CPU-intensive process (not to mention the actual filtering).
        if not self._filtered_noise_token_valid:
            log.debug('recomputing filtered noise token')
            # Get the current values of the parameters
            rp = self.get_current_value('rp')
            rs = self.get_current_value('rs')
            order = self.get_current_value('order')
            fc = self.get_current_value('fc')
            bandwidth = self.get_current_value('bandwidth')
            fs = self.iface_behavior.fs

            # Compute the filter coefficients
            fl = np.clip(fc-0.5*bandwidth, 0, 0.5*fs)
            fh = np.clip(fc+0.5*bandwidth, 0, 0.5*fs)
            Wp = np.array([fl, fh])/(0.5*fs)
            b, a = signal.iirfilter(order, Wp, rp, rs, ftype='elliptic')

            noise_token = self._get_noise_token()

            # Filter and cache the token
            token = signal.filtfilt(b, a, noise_token)
            self._filtered_noise_token = token
            self._filtered_noise_token_valid = True

        return self._filtered_noise_token

    def _get_sam_envelope(self):
        # This part is not as CPU-intensive, but serves a good example of how to
        # cache the pieces for generating the final token.
        if not self._sam_envelope_valid:
            log.debug('recomputing sam envelope')
            fm = self.get_current_value('fm')
            depth = self.get_current_value('modulation_depth')
            delay = self.get_current_value('modulation_onset')
            direction = self.get_current_value('modulation_direction')
            t = self._get_time()

            if delay == 0: 
                eq_phase = wave.sam_eq_phase(depth, direction)
            else:
                eq_phase = -np.pi

            envelope = depth/2*np.cos(2*np.pi*fm*t+eq_phase)+1-depth/2

            # Ensure that we scale the waveform so that the total power remains
            # equal to that of an unmodulated token.
            envelope *= 1.0/wave.sam_eq_power(depth)

            delay_n = int(delay*self.iface_behavior.fs)
            if delay_n > 0:
                delay_envelope = np.ones(delay_n)
                envelope = np.concatenate((delay_envelope, envelope[:-delay_n]))

            self._sam_envelope = envelope
            self._sam_envelope_valid = True

        return self._sam_envelope

    def _get_cos_envelope(self):
        if not self._cos_envelope_valid:
            log.debug('recomputing cos envelope')
            t = self._get_time()
            rise_time = self.get_current_value('rise_fall_time')
            rise_n = int(rise_time*self.iface_behavior.fs)
            duration_n = len(t)
            envelope = wave.generate_envelope(duration_n, rise_n) 
            self._cos_envelope = envelope
            self._cos_envelope_valid = True
        return self._cos_envelope

    ########################################################################
    # Actual waveform computation
    ########################################################################

    def compute_waveform(self, calibration, hw_attenuation=0):
        # This is where we take the precomputed pieces that we cached and
        # combine them to generate the final waveform that will be uploaded to
        # the buffer.  Note that this function actually does very little because
        # many of the computations have been cached and updated only when the
        # relevant parameters change.

        # In theory, if we did not wish to cache the computations, then we could
        # perform all of the relevant steps (updating attenuation, computing
        # scaling factor, computing token, computing modulation envelope,
        # computing cosine envelope) in this function.

        # Compute the required attenuation 
        level = self.get_current_value('level')
        fc = self.get_current_value('fc')
        attenuation = calibration.get_spl(fc, voltage=MAX_VRMS)-level

        # Get the cached waveforms.  Always use the self._get_waveform_name() methods
        # rather than self._waveform_name because the self._get_waveform_name()
        # method will check to see if the waveform needs to be recomputed.  If
        # the waveform does not need to be recomputed, the cached value will be
        # returned.
        token = self._get_filtered_noise_token()
        sam_envelope = self._get_sam_envelope()
        cos_envelope = self._get_cos_envelope()

        return token*sam_envelope*cos_envelope, attenuation

    def set_duration(self, value):
        # Note that I don't worry about the sampling frequency of the buffer_out
        # changing because this is already established by the time the user hits
        # the "run" button to start the experiment.
        self.iface_behavior.cset_tag('signal_dur_n', value, 's', 'n')
        self._time_valid = False


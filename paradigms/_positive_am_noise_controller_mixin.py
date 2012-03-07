from traits.api import HasTraits, Any, Bool

# For generating the signal
from cns import signal as wave
import numpy as np
from scipy import signal
from cns import get_config
voltage = get_config('MAX_SPEAKER_DAC_VOLTAGE')

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
        self._update_attenuation()

    ########################################################################
    # Methods for computing/caching waveform
    ########################################################################

    def _get_time(self):
        if not self._time_valid:
            duration = self.get_current_value('duration')
            self._time = wave.time(self.buffer_out.fs, duration)
        return self._time
        
    def _get_noise_token(self):
        # Compute the noise waveform (using the seed)
        if not self._noise_token_valid:
            seed = self.get_current_value('seed')
            state = np.random.RandomState(seed)
            token = state.uniform(low=-1, high=1, size=len(self._time))
            self._noise_token = token
            self._filtered_noise_token_valid = False
        return self._noise_token

    def _recompute_filtered_noise_token(self):
        # Compute the filtered waveform using the cached noise waveform.  Note
        # that we do this caching because computing filter coefficients can be a
        # CPU-intensive process (not to mention the actual filtering).

        # Get the current values of the parameters
        rp = self.get_current_value('rp')
        rs = self.get_current_value('rs')
        order = self.get_current_value('order')
        fc = self.get_current_value('fc')
        bandwidth = self.get_current_value('bandwidth')
        fs = self.buffer_out.fs

        # Compute the filter coefficients
        fl = np.clip(fc-0.5*bandwidth, 0, 0.5*fs)
        fh = np.clip(fc+0.5*bandwidth, 0, 0.5*fs)
        Wp = np.array([fl, fh])/(0.5*fs)
        b, a = signal.iirfilter(order, Wp, rp, rs, ftype='elliptic')

        # Filter and cache the token
        token = signal.filtfilt(b, a, self._noise_token)
        self._filtered_noise_token = token

    def _recompute_sam_envelope(self):
        # This part is not as CPU-intensive, but serves a good example of how to
        # cache the pieces for generating the final token.
        fm = self.get_current_value('fm')
        depth = self.get_current_value('depth')
        delay = self.get_current_value('modulation_onset')
        direction = self.get_current_value('modulation_direction')

        if delay == 0: 
            eq_phase = wave.sam_eq_phase(depth, direction)
        else:
            eq_phase = -np.pi

        envelope = depth/2*np.cos(2*np.pi*fm*self._time+eq_phase)+1-depth/2

        # Ensure that we scale the waveform so that the total power remains
        # equal to that of an unmodulated token.
        envelope *= 1.0/wave.sam_eq_power(depth)

        delay_n = int(delay*self.buffer_out.fs)
        if delay_n > 0:
            delay_envelope = np.ones(delay_n)
            envelope = np.concatenate((delay_envelope, envelope[:-delay_n]))
        self._sam_envelope = envelope

    def _recompute_cos_envelope(self):
        rise_time = self.get_current_value('rise_fall_time')
        rise_n = int(rise_time*self.buffer_out.fs)
        duration_n = len(self._time)
        envelope = wave.generate_envelope(duration_n, rise_n) 
        self._cos_envelope = envelope

    ########################################################################
    # Set the hardware attenuators and compute required scaling factor
    ########################################################################
    # Note that this is an overly simplistic (and non-standard) of computing the
    # dB SPL for a noise token; however, I will leave this as-is.

    def set_level(self, level):
        self._update_attenuation()

    def _get_attenuation(self, fc, level, calibration):
        # Helper method for set_level
        dBSPL_RMS = calibration.get_spl(fc, voltage=1)
        attenuation = dBSPL_RMS-level
        if attenuation < 0:
            raise ValueError, 'Cannot achieve requested SPL'
        elif attenuation >= 120.0:
            attenuation = 120.0
        return attenuation

    def _update_attenuation(self):
        fc = self.get_current_value('fc')
        level = self.get_current_value('level')
        att1 = self._get_attenuation(fc, level, self.cal_primary)
        att2 = self._get_attenuation(fc, level, self.cal_secondary)

        # Here, I think of this as "software" (sw) attenuation (e.g. achieving
        # the attenuation via digital scaling of the waveform).  
        sw_att1, sw_att2 = self.set_attenuations(att1, att2)
        self._sw_att1 = sw_att1
        self._sw_att2 = sw_att2

    ########################################################################
    # Actual waveform computation
    ########################################################################

    def compute_waveform(self):
        # This is where we take the precomputed pieces that we cached and
        # combine them to generate the final waveform that will be uploaded to
        # the buffer.  Note that this function actually does very little because
        # many of the computations have been cached and updated only when the
        # relevant parameters change.

        # In theory, if we did not wish to cache the computations, then we could
        # perform all of the relevant steps (updating attenuation, computing
        # scaling factor, computing token, computing modulation envelope,
        # computing cosine envelope) in this function.

        # The hardware attenuators have been configured in the set_level method
        # and the remaining attenuation required via scaling (sw_att1 and
        # sw_att2) has been cached in the relevant attributes.  Look up the
        # required attenuation and scale the waveform accordingly.
        speaker = self.get_current_value('speaker')
        if speaker == 'primary':
            sw_att = self.sw_att1
        else:
            sw_att = self.sw_att2
        sf = 10**(-sw_att/20.0)

        # Get the cached waveforms
        token = self._filtered_noise_token
        sam_envelope = self._sam_envelope
        cos_envelope = self._cos_envelope

        # Return the result
        return sf*token*sam_envelope*cos_envelope

    def set_duration(self, value):
        # Note that I don't worry about the sampling frequency of the buffer_out
        # changing because this is already established by the time the user hits
        # the "run" button to start the experiment.
        self._time = wave.time(self.buffer_out.fs, value)

        # We don't need to call self._recompute_filtered_noise_token() because
        # self._recompute_noise_token() does so.
        self._recompute_noise_token()
        self._recompute_sam_envelope()
        self._recompute_cos_envelope()
        self.iface_behavior.cset_tag('signal_dur_n', value, 's', 'n')

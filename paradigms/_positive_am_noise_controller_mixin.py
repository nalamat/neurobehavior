from traits.api import HasTraits, Any

# For generating the signal
from cns import signal as wave
import numpy as np
from scipy import signal

class PositiveAMNoiseControllerMixin(HasTraits):

    #########################################################################
    # Cached waveforms to speed up computation
    #########################################################################

    _time = Any
    _cos_envelope = Any
    _sam_envelope = Any
    _noise_token = Any
    _filtered_noise_token = Any

    #########################################################################
    # Trigger recomputation of cosine envelope when rise time changes
    ########################################################################

    def set_rise_fall_time(self, value):
        self._recompute_cos_envelope()

    #########################################################################
    # Trigger recomputation of SAM envelope when modulation changes
    ########################################################################

    def set_fm(self, value):
        self._recompute_sam_envelope()

    def set_modulation_depth(self, value):
        self._recompute_sam_envelope()
        
    def set_modulation_direction(self, value):
        self._recompute_sam_envelope()

    def set_modulation_onset(self, value):
        self._recompute_sam_envelope()

    #########################################################################
    # Trigger recomputation of base noise token when seed changes
    #########################################################################

    def set_seed(self, value):
        self._noise_token()

    #########################################################################
    # Trigger recomputation of filter noise token when filter settings change
    #########################################################################

    def set_fc(self, value):
        self._recompute_filtered_noise_token()

    def set_rp(self, value):
        self._recompute_filtered_noise_token()

    def set_rs(self, value):
        self._recompute_filtered_noise_token()

    def set_order(self, value):
        self._recompute_filtered_noise_token()

    def set_bandwidth(self, value):
        self._recompute_filtered_noise_token()

    #########################################################################
    # Methods for computing/caching waveform
    #########################################################################

    def _recompute_time(self):
        duration = self.get_current_value('duration')
        self._time = wave.time(self.buffer_out.fs, duration)
        
    def _recompute_noise_token(self):
        # Compute the noise waveform (using the seed)
        seed = self.get_current_value('seed')
        state = np.random.RandomState(seed)
        token = state.uniform(low=-1, high=1, size=len(self._time))
        self._noise_token = token
        self._recompute_filtered_noise_token()

    def _recompute_filtered_noise_token(self):
        # Compute the filtered waveform using the cached noise waveform.  Note
        # that we do this caching because computing filter coefficients can be a
        # CPU-intensive process.

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
        delay = self.get_current_value('modulation_onset')
        fm = self.get_current_value('fm')
        depth = self.get_current_value('depth')
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

    def compute_waveform(self):
        level = self.get_current_value('level')

        # TODO - compute attenuation and scaling factor here.  Need to talk to
        # GvT about what he has been using.

        #fc = self.get_current_value('fc')
        #calibration.get_sf(fc, level)

        # Get the cached waveforms
        token = self._filtered_noise_token
        sam_envelope = self._sam_envelope
        cos_envelope = self._cos_envelope

        return token*sam_envelope*cos_envelope

    def set_duration(self, value):
        # Note that I don't worry about the sampling frequency of the buffer_out
        # changing because this is already established by the time the user hits
        # the "run" button to start the experiment.
        self._time = wave.time(self.buffer_out.fs, value)
        self._recompute_noise_token()
        self._recompute_sam_envelope()
        self._recompute_cos_envelope()
        self.iface_behavior.cset_tag('signal_dur_n', value, 's', 'n')

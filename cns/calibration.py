from cns.sigtools import patodb, dbtopa

from scipy import signal
import numpy as np
import os

import logging
log = logging.getLogger(__name__)

def db(target, reference=1):
    return 20*np.log10(target/reference)

#def nearest(target, values):
#    unique_values = np.unique(values)
#    i = np.abs(values-target).argmin()
#    return unique_values[i]
#
#def nearest_mask(target, values):
#    value = nearest(target, values)
#    mask = values == value
#    return value, mask

def weights(target, values, check_bounds=False):
    '''
    Given an array of monotonically increasing values and a target value, return
    an array of weights that can be used to interpolate the target value.

    >>> x = [5, 10, 15, 20, 30]
    >>> y = [1, .5, .2, .1, 10]
    >>> w = weights(7.5, x)
    >>> print np.average(y, weights=w)
    0.75

    >>> w = weights(15, x)
    >>> print np.average(y, weights=w)
    0.2

    >>> w = weights(6, x)
    >>> print np.average(y, weights=w)
    0.9

    >>> print weights(1.5, [0, 1, 2, 3, 4, 5]).tolist()
    [0.0, 0.5, 0.5, 0.0, 0.0, 0.0]

    >>> print weights(4.75, [0, 1, 2, 3, 4, 5]).tolist()
    [0.0, 0.0, 0.0, 0.0, 0.25, 0.75]

    >>> print weights(3, [0, 1, 2, 3, 4, 5]).tolist()
    [0.0, 0.0, 0.0, 1.0, 0.0, 0.0]

    >>> print weights(10, [1]).tolist()
    [1.0]

    >>> weights(10, [1], check_bounds=True).tolist()
    Traceback (most recent call last):
        ...
    ValueError: Threshold out of bounds

    '''
    values = np.asanyarray(values)
    indices = np.arange(len(values))
    if check_bounds:
        threshold = np.interp(target, values, indices, np.nan, np.nan)
        if np.isnan(threshold):
            raise ValueError, "Threshold out of bounds"
    else:
        threshold = np.interp(target, values, indices)

    i, weight = divmod(threshold, 1)
    weights = np.zeros(values.shape)
    weights[i] = 1-weight
    try:
        weights[i+1] = weight
    except IndexError:
        pass
    return weights

calibration_dtype = [('gain', 'd'), 
                     ('voltage', 'd'), 
                     ('frequency', 'd'),
                     ('spl', 'd'), 
                     ('phase', 'd'),
                     ]

def load_mat_cal(name, equalized=False):
    '''
    Read calibration files generated by Sharad's FIRCal routine (note that you
    must use the version modified by Brad Buran).

    name : string
        Path of file to load
    equalized: boolean
        Return a calibration that assumes the speakers are equalized (i.e.
        uniform output in dB SPL across the frequency range of interest).
        Requires that both RMS and FIR calibration data are saved in the
        calibration file.

    Note that the FIRCal compensates for what it thinks the reference gain is so
    max SPL reflects what you will expect given an output gain of 0 dB.
    '''
    # Helper functions for accessing scalar and vector values stored in the
    # Matlab structure
    get_scalar = lambda x: x.ravel()[0].ravel()[0]
    get_vector = lambda x: x.ravel()[0].ravel()
    from scipy.io import loadmat
    struct = loadmat(name)

    if equalized:
        # Load the Vrms versus dB SPL data
        vrms = get_vector(struct['rmscal']['v_rms'])
        spl = get_vector(struct['rmscal']['dbspl'])
        fl = np.ones(len(vrms)) * get_scalar(struct['rmscal']['Flo'])
        fh = np.ones(len(vrms)) * get_scalar(struct['rmscal']['Fhi'])
        gain = np.zeros(len(vrms))
        phase = np.zeros(len(vrms))

        fl_cal = np.c_[gain, vrms, fl, spl, phase]
        fh_cal = np.c_[gain, vrms, fh, spl, phase]
        calibration = np.r_[fl_cal, fh_cal]

        # Load the speaker impulse response
        impulse = get_vector(struct['fircal']['Impulse'])
        impulse_fs = get_scalar(struct['fircal']['Fs'])

        # Load the correction factors
        freq_correction = get_vector(struct['golaycal']['freq']) 
        mag_correction = get_vector(struct['golaycal']['maginv']) 
        phase_correction = get_vector(struct['golaycal']['phase']) 

        calibration = EqualizedCalibration(calibration, impulse, impulse_fs,
                                           freq_correction, mag_correction,
                                           phase_correction)
        return calibration
    else:
        freq = get_vector(struct['sinecal']['freq'])
        mag = get_vector(struct['sinecal']['mag'])
        phase = get_vector(struct['sinecal']['phase'])
        # The tone waveform run by FIRCal is scaled by DAScale, so we need to
        # pull this value in as the test voltage.
        voltage = np.ones(len(freq)) * get_scalar(struct['sinecal']['DAscale'])
        # Note that there is a Gain reported in the FIRCal calibration file;
        # however, this refers to the microphone gain not the output gain.
        gain = np.zeros(len(freq))
        calibration = np.c_[gain, voltage, freq, mag, phase]
        return Calibration(calibration)

def plot_cal(calibration, frequencies=None, target_voltage=1, target_gain=0,
             figure=None):

    if figure is None:
        from pylab import gcf
        fig = gcf()
    if calibration.fir_coefficients is not None:
        # Split figure into two subplots and plot the impulse response
        splax = fig.add_subplot(211)
        firax = fig.add_subplot(212)
        t = np.arange(len(calibration.fir_coefficients))/calibration.fir_fs
        firax.plot(t, calibration.fir_coefficients, 'k')
        firax.grid(True)
        firax.set_xlabel('Time (s)')
        firax.set_ylabel('Amplitude')
    else:
        splax = fig.add_subplot(111)
    reference = calibration.ref_frequencies
    reference_spl = calibration.get_max_spl(reference)
    splax.semilogx(reference, reference_spl, 'k')
    splax.semilogx(reference, reference_spl, 'bo')
    splax.set_xlabel('Frequency (Hz)')
    ylabel = 'Output at {} Vrms and {} dB gain (dB SPL)'
    splax.set_ylabel(ylabel.format(target_voltage, target_gain))
    splax.grid(True)
    if frequencies is not None:
        max_spl = calibration.get_max_spl(frequencies)
        splax.plot(frequencies, max_spl, 'ro')

def valid_calibration(*calibrations):
    '''
    Given an array of calibration objects, return an array (of the same length)
    with the frequencies truncated so that all calibrations are identical
    '''
    # TODO: the actual implementation
    raise NotImplementedError

class Calibration(object):
    '''
    Calibration data is stored in a 3D array with the indices corresponding to
    gain, voltage and frequency.  Typically calibration is only done at one gain
    and voltage; however, this gives us the flexibility to calibrate non-linear
    systems (to a limited extent).  We can, in the future, incorporate more
    "dimensions" (e.g. the attenuator setting).

    In this context, gain reflects the total gain of all manually-controlled
    elements in the system (e.g. such as the Crown D75A amplifier).  Elements
    that are controlled by the computer (e.g. a programmable attenuator) are
    considered separately.  Note that gain can be a negative number.

    reference : ndarray of floats, shape (npoints, 5) (required)
    
        Reference measurement values. Each row indicates reference gain,
        reference voltage, reference frequency, measured SPL and measured phase.

    Typically we have only one test gain and voltage; however, I don't see a
    reason why we can't support calibration of non-linear systems as long as
    we test the system at known points. This would be particularly useful when
    we're driving the system near the limits (the speaker begins to distort
    when you are playing it too loud).  Note that if multiple test gains and
    voltages are provided, the system will perform a linear interpolation.

    check_bounds : A dictionary or { None, 'exact', 'bounds' } (optional)

        None indicates no error checking is done, 'exact' ensures that specified
        gains, voltages and frequencies coincide with calibrated values and
        'bounds' ensures that specified gains, voltages and frequencies fall
        within the lower and upper bounds of the test values.

        If None, 'exact' or 'bounds' is passed, the error-checking behavior is
        set for all three.  Otherwise, a dictionary can be specified that
        controls the error-checking behavior for each setting.  For example:

            { 'gain'        : 'exact',
              'voltage'     : None,
              'frequency'   : 'bounds', }

    fir_coefficients : array (optional)

        Coefficients of finite impulse response (FIR) filter used to flatten the
        waveform.  These coefficients may either be uploaded to a digital FIR
        filter in a DSP or applied directly to a waveform using the
        `Calibration.equalize` method.  Note that you must provide

    fir_fs : float (required if fir_coefficient is provided) 
    '''

    def __init__(self, reference, fir_coefficients=None, fir_fs=None,
                 check_mode=None):

        # Convert to a Numpy record array (with named fields) to facilitate data
        # indexing and sorting
        #self.reference = np.array(reference).T.astype(calibration_dtype)
        reference = np.asanyarray(reference)
        self.reference = np.rec.fromarrays(reference.T, dtype=calibration_dtype)
        self.reference.sort(axis=0)

        self.ref_gains = np.unique(self.reference['gain'])
        self.ref_voltages = np.unique(self.reference['voltage'])
        self.ref_frequencies = np.unique(self.reference['frequency'])
        self.ref_spl = self.reference['spl']
        self.ref_phi = self.reference['phase']

        # Ensure that valid error-checking modes were passed for check_mode
        valid_modes = (None, 'exact', 'bounds')
        mode_error = 'Invalid mode for check_bounds'
        if type(check_mode) == type({}):
            if self.check_mode['gain'] not in valid_modes:
                raise ValueError, mode_error
            if self.check_mode['voltage'] not in valid_modes:
                raise ValueError, mode_error
            if self.check_mode['frequency'] not in valid_modes:
                raise ValueError, mode_error
            self.check_mode = check_mode
        elif check_mode not in valid_modes:
            raise ValueError, 'Invalid mode %s for check_bounds' % check_mode
        else:
            self.check_mode = {}
            self.check_mode['gain'] = check_mode
            self.check_mode['voltage'] = check_mode
            self.check_mode['frequency'] = check_mode
        
        # Reformat reference into a 3D arrays that we can use for trilinear
        # interpolation to estimate max SPL and average phase shift.
        gains = len(self.ref_gains)
        voltages = len(self.ref_voltages)
        frequencies = len(self.ref_frequencies)
        new_shape = gains, voltages, frequencies
        self.ref_spl.shape = new_shape
        self.ref_phi.shape = new_shape

        # Prepare the FIR coefficients for use
        self.fir_coefficients = fir_coefficients
        if fir_coefficients is not None:
            self.fir_zi = signal.lfiltic(fir_coefficients, 1, 0)
            if fir_fs is None:
                mesg = 'Must provide sampling frequency for fir_coefficients' 
                raise ValueError(mesg)
            self.fir_fs = fir_fs

    def _validate_value(self, value_type, target_values, calibrated_values):
        check_mode = self.check_mode[value_type]
        if check_mode == 'exact':
            # Ensure that all target values are in the calibrated values.  This
            # can handle both a single target value (scalar) and array of target
            # values (vector).
            valid = np.in1d(target_values, calibrated_values, True)
            if not np.all(valid):
                mesg = 'No calibration data for %s of %f'
                raise ValueError, mesg % (value_type, target_value)
        if check_mode == 'bounds':
            lb_check = target_value >= calibrated_values[0]
            ub_check = target_value <= calibrated_values[-1]
            if not (np.all(lb_check) and np.all(ub_check)):
                mesg = 'Requested %s of %f outside calibrated range'
                raise ValueError, mesg % (value_type, target_value)

    def _reduce_spl(self, a, target_voltage, target_gain):
        '''
        Performs bilinear interpolation, first across gain then voltage,
        returning a 1D array of SPL as a function of frequency
        '''
        # First, we do a linear interpolation along the gain axis to estimate
        # the maximum SPL at our desired gain.  During this interpolation
        # process, we reduce the array to a 2D array (voltage, frequency)
        self._validate_value('gain', target_gain, self.ref_gains)
        gain_weights = weights(target_gain, self.ref_gains)
        a = np.sum(a*gain_weights[..., np.newaxis, np.newaxis], axis=0)
        cal_gain = np.average(self.ref_gains, weights=gain_weights)
        gain_correction = target_gain-cal_gain
        a += gain_correction

        log.debug('%s: cal gain %f, target gain %f, correction %f', 
                self, cal_gain, target_gain, gain_correction)

        # Now we do a linear interpolation across the voltage axis, reducing the
        # array to a 1D array (frequency)
        self._validate_value('voltage', target_voltage, self.ref_voltages)
        voltage_weights = weights(target_voltage, self.ref_voltages)
        a = np.sum(a*voltage_weights[..., np.newaxis], axis=0)
        cal_voltage = np.average(self.ref_voltages, weights=voltage_weights)
        voltage_correction = db(target_voltage, cal_voltage)
        a += voltage_correction

        log.debug('%s: cal voltage %f, target voltage %f, correction %f', 
                self, cal_voltage, target_voltage, voltage_correction)

        return a

    def get_spl(self, frequencies, voltage=1, gain=0):
        '''
        Computes expected speaker output (in dB SPL) for tones at the specified
        frequencies assuming 0 dB attenuation

        Parameters
        ----------
        frequencies : array-like (Hz)
            The frequencies to compute
        voltage : float (V)
            The target amplitude of the tone.  Note that whether it's peak to peak or RMS depends on how the calibration data was generated.  I believe FIRCal uses RMS (either case it's "only" 3 dB difference.
        gain : float (dB power)
            The output gain of the system
            
        In theory we could support multiple target voltages and gains; however,
        since we can only output a single target voltage and gain for any given
        waveform, only frequencies can be a sequence.
        '''
        ref_spl = self._reduce_spl(self.ref_spl, voltage, gain)
        max_spl = np.interp(frequencies, self.ref_frequencies, ref_spl)
        log.debug('%s: max output for %r is %r with gain %f and voltage %f',
                self, frequencies, max_spl, gain, voltage)
        return max_spl
    
    def get_max_spl(self, frequencies, voltage=1, gain=0):
        '''
        This is a DEPRECATED method to support code that just calls get_max_spl
        
        This is not an accurately-named method and is misleading (blame EPL).
        '''
        return self.get_spl(frequencies, voltage, gain)

    def get_mean_spl(self, flow, fhigh, voltage=1, gain=0, mode='spectrum',
            endpoint=False):
        '''
        Computes average speaker output (in dB SPL) across given frequency range

        If the spacing of calibration frequencies is linear, then each
        calibration point in the frequency range can be treated equally and the
        average SPL will be computed as:

        .. math::
            mean SPL = log10( (10^(SPL_1) + 10^(SPL_2) ... + 10^(SPL_N)) / N)

        Note that, implementation-wise, we actually divide each value by 20
        before converting to a linear scale and then multiply the result by 20
        after converting back to a log scale.

        Parameters
        ----------
        flow : float (Hz)
            The lower bound of the range
        fhigh : float (Hz)
            The upper bound of the range
        voltage : int or float, optional (V)
            The intended peak to peak amplitude of the output
        gain : int or float, optional (dB power)
            The intended gain of the system
        mode : {'spectrum', 'band'}
            Whether to return the spectrum level or band level of the noise.
        weighting : {'geometric', 'arithmetic'}
            Weighting mode for averaging the speaker output across frequencies.
            #TODO expand on this more.  This is not implemented at the moment
            anyway.
        endpoint : bool, optional
            If True, evaluate mean SPL over the closed interval [flow, fhigh],
            otherwise, evaluate over the half-open interval [flow, fhigh).
            Default is False.

        Relationship between band level and spectrum level

        .. math:: 
            band_level = spectrum_level + 10*log10(\delta f)
        '''
        ref_spl = self._reduce_spl(self.ref_spl, voltage, gain)
        mask = self.ref_frequencies >= flow
        if endpoint:
            mask = mask & (self.ref_frequencies <= fhigh)
        else:
            mask = mask & (self.ref_frequencies < fhigh)

        #if weighting == 'geometric':
        #    pass
        #elif weighting == 'arithmetic':
        #    pass
        #else:
        #    raise ValueError, 'Unsupported weighting %s' % weighting

        mean_spl = patodb(np.mean(dbtopa(ref_spl[mask])))
        if mode == 'spectrum':
            return mean_spl
        elif mode == 'band':
            return mean_spl + 10.0*np.log10(fhigh-flow)
        else:
            raise ValueError, 'Unsupported mode %s' % mode

    def _reduce_phase(self, a, target_voltage, target_gain):
        '''
        Performs bilinear interpolation, first across gain then voltage,
        returning a 1D array of phase as a function of frequency.
        '''
        # First, we do a linear interpolation along the gain axis to estimate
        # the phase at our desired gain.  During this interpolation process, we
        # reduce the array to a 2D array (voltage, frequency)
        self._validate_value('gain', target_gain, self.ref_gains)
        gain_weights = weights(target_gain, self.ref_gains)
        a = np.sum(a*gain_weights[..., np.newaxis, np.newaxis], axis=0)

        # Now we do a linear interpolation across the voltage axis, reducing the
        # array to a 1D array (frequency)
        self._validate_value('voltage', target_voltage, self.ref_voltages)
        voltage_weights = weights(target_voltage, self.ref_voltages)
        a = np.sum(a*voltage_weights[..., np.newaxis], axis=0)

        return a

    def get_phase(self, frequencies, voltage=1, gain=0):
        ref_phase = self._reduce_phase(self.ref_phi, voltage, gain) 
        ref_phase = np.unwrap(ref_phase)
        return np.interp(frequencies, self.ref_frequencies, ref_phase)

    def get_sf(self, frequency, level, attenuation):
        '''
        Return scaling factor required to achieve required attenuation
        '''
        spl = self.get_spl(frequency)
        discrepancy = spl-level-attenuation
        sf = 1.0/(10**(discrepancy/20.0))
        log.debug('%s: output is %f dB SPL, hw atten is %f dB',
                  self, spl, attenuation), 
        log.debug('%s: must scale by %f to achieve remaining %f dB', self, sf,
                  discrepancy)
        return sf

    def get_attenuation(self, frequency, level):
        return self.get_max_spl(frequency)-level

    def equalize(self, waveform):
        if self.fir_coefficients is None:
            raise ValueError, "No FIR data available"
        return signal.lfilter(self.fir_coefficients, 1, waveform)
    
    def get_best_attenuation(self, expected_range, voltage=1, gain=0):
        '''
        Get the attenuation to use given the expected range of frequencies and
        levels in the series

        Parameters
        ----------
        expected_range : array-like
            First column specifies frequency, second column specifies the
            corresponding maximum level (in dB SPL) desired for that frequency.
        voltage
            The intended peak to peak amplitude of the output
        gain
            The intended gain of the system
        '''
        expected_range = np.array(expected_range)
        if expected_range.ndim != 2 or expected_range.shape[1] != 2:
            raise ValueError, "Expected range is in wrong format"
        if len(expected_range) == 0:
            raise ValueError, "Must provide an expected range"
        frequencies = expected_range[:,0]
        target_spl = expected_range[:,1]
        max_spl = self.get_max_spl(expected_range[:,0], voltage, gain)
        return np.min(max_spl-target_spl)

    def get_nearest_frequency(self, frequencies, mode='round'):
        '''
        Return the nearest reference frequency for the given frequencies

        Typically used to coerce your stimuli to the nearest frequency for which
        a calibration datapoint is available.
        '''
        if mode not in ('round', 'ceil', 'floor'):
            raise ValueError, 'Unsupported mode {}'.format(mode)
        mode_func = getattr(np, mode)
        indices = np.arange(len(self.ref_frequencies))
        interp_indices = np.interp(frequencies, self.ref_frequencies, indices)
        nearest_indices = mode_func(interp_indices).astype('i')
        return self.ref_frequencies[nearest_indices]

    def __repr__(self):
        return '<Calibration>'

class EqualizedCalibration(Calibration):

    '''
    Assumes the system is flat across the frequency range of interest and
    perfectly linear.

    spl : int or float 
        Output of system (in dB SPL) between [freq_lb, freq_ub) at the specified
        gain and voltage.  Defaults to 100 dB SPL.

    gain : int or float
        Output gain of system.  Typically this reflects what the gain of the
        amplifier was set to.  If you *never* change the gain of the amplifier,
        you can safely leave this at 0.
    
    voltage : int or float (optional)
        RMS voltage used to generate calibration data

    freq_lb : int or float (optional)
        Lower bound of calibrated frequency range

    freq_ub : int or float (optional)
        Upper bound of calibrated frequency range

    args and kwargs will be passed to Calibration
    '''
    
    def __init__(self, calibration, impulse, impulse_fs, transfer_freq,
                 transfer_mag_inv, transfer_phase, gain=0, voltage=1):
        # Exploit the standard calibration logic by providing "flat" reference
        # data
        super(EqualizedCalibration, self).__init__(calibration, impulse, impulse_fs)
        self.transfer_freq = transfer_freq
        self.transfer_mag_inv = transfer_mag_inv
        self.transfer_phase = transfer_phase

    def get_fft_mag_correction(self, frequencies):
        return np.interp(frequencies, self.transfer_freq, self.transfer_mag_inv)

    def get_fft_phase_correction(self, frequencies):
        return np.interp(frequencies, self.transfer_freq, self.transfer_phase)

class Attenuation(Calibration):

    '''
    Allows the user to specify level in dB attenuation.  This is for
    backwards-compatibility with legacy paradigms where the signal level was
    controlled by having the user specify the actual attenuation.  
    
    Note that attenuation must be specified as a negative value.  For example,
    if you wish to have 80 dB of attenuation, enter -80.

    In general, this should serve as a drop-in replacement wherever you would
    otherwise use the standard calibration system.
    '''

    def __init__(self, gain=0, vrms=1, freq_lb=0, freq_ub=100e3):
        fl_cal = np.c_[gain, vrms, freq_lb, 0, 0]
        fh_cal = np.c_[gain, vrms, freq_ub, 0, 0]
        calibration = np.r_[fl_cal, fh_cal]
        super(Attenuation, self).__init__(calibration)

class PlotCalibration(EqualizedCalibration):

    '''
    Waveforms will be plotted as if dB was a linear value

    A 20 dB SPL tone will appear to be half the height of a 40 dB SPL tone even
    though the *correct* amplitude difference is a factor of 10.
    '''

    def get_sf(self, frequency, level, attenuation):
        '''
        Return scaling factor required to achieve attenuation
        '''
        max_spl = self.get_max_spl(frequency)
        discrepancy = max_spl-level-attenuation
        return discrepancy/max_spl

import unittest

class TestToneCalibration(unittest.TestCase):

    def setUp(self):
        # Each row is gain, voltage, frequency, spl, phase
        calibration_data = np.array([
            [0, 3,  100,    111,    1],
            [0, 3,  200,    112,    1],
            [0, 3,  300,    113,    1],
            [0, 3,  400,    110,    1],
            [0, 3,  500,    111,    1],

            [0, 1,  100,    122,    1],
            [0, 1,  200,    125,    1],
            [0, 1,  300,    127,    1],
            [0, 1,  400,    128,    1],
            [0, 1,  500,    129,    1],

            [0, 2,  200,    115,    1],
            [0, 2,  400,    117,    1],
            [0, 2,  300,    115,    1],
            [0, 2,  500,    115,    1],
            [0, 2,  100,    117,    1],

            #[5, 2,  200,    118,    1],
            #[5, 2,  500,    119,    1],
            #[5, 2,  400,    121,    1],
            #[5, 2,  300,    120,    1],
            #[5, 2,  100,    123,    1],
            ])
        self.calibration = Calibration(calibration_data)

    def testMaxSPL(self):
        result = self.calibration.get_max_spl([200, 400])
        self.assertEqual(result.tolist(), [125, 128])
        result = self.calibration.get_max_spl(200, voltage=2)
        self.assertEqual(result, 115)
        result = self.calibration.get_max_spl(200, voltage=1.5)
        self.assertEqual(result, 120)
        result = self.calibration.get_max_spl(150, voltage=1.5)
        self.assertEqual(result, 119.75)

    def testMeanSPL(self):
        result = self.calibration.get_mean_spl(200, 500, endpoint=True)
        self.assertAlmostEqual(result, 127.372495844248)
        result = self.calibration.get_mean_spl(200, 600, mode='band')
        self.assertAlmostEqual(result, 127.372495844248+10*np.log10(600-200))

class TestEqualizedCalibration(unittest.TestCase):

    def setUp(self):
        calibration_data = np.array([
            [0, 1,  100,    111,    1],
            [0, 2,  100,    112,    1],
            [0, 3,  100,    113,    1],
            [0, 4,  100,    110,    1],
            [0, 5,  100,    111,    1],
            ])
        self.calibration = Calibration(calibration_data)

    def testMaxSPL(self):
        result = self.calibration.get_max_spl([200, 400])
        self.assertEqual(result.tolist(), [111, 111])
        result = self.calibration.get_max_spl(200, voltage=2)
        self.assertEqual(result, 112)
        result = self.calibration.get_max_spl(200, voltage=4.5)
        self.assertEqual(result, 110.5)
        result = self.calibration.get_max_spl(150, voltage=1.5)
        self.assertEqual(result, 111.5)

class TestAttenuationCalibration(unittest.TestCase):

    def setUp(self):
        self.calibration = Attenuation()

    def testAttenuation(self):
        result = self.calibration.get_attenuation(100, 80)
        self.assertEqual(result, -80)
        result = self.calibration.get_attenuation(100, 0)
        self.assertEqual(result, 0)
        result = self.calibration.get_attenuation([100, 500], -20.5)
        self.assertEqual(result.tolist(), [20.5, 20.5])

    def testScalingFactor(self):
        result = self.calibration.get_sf(100, -80, 80)
        self.assertEqual(result, 1.0)
        result = self.calibration.get_sf(100, -60, 80)
        self.assertEqual(result, 10.0)
        result = self.calibration.get_sf(100, -60, 40)
        self.assertEqual(result, 0.1)

if __name__ == '__main__':
    import logging, sys, doctest
    #logging.basicConfig(stream=sys.stderr)
    #logging.getLogger().setLevel(logging.DEBUG)
    doctest.testmod()
    unittest.main()

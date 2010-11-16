#__all__ = [ Tone, Noise, FM ]

from scipy import signal
from numpy import inf, nan, pi, sin, cos, divide, random, linspace, ones
import numpy as np

################################################################################
# Utility functions
################################################################################
def t(fs, duration):
    '''
    Generate time vector for computing signal waveform.

    Parameters
    ----------
    fs : number (Hz)
        sampling frequency
    duration : (s)
        duration of vector

    Returns
    -------
    array [fs**-1, 2*fs**-1 ... duration]

    Due to strange boundary effects occuring at zero in some of the block
    computations (particularly when we are normalizing an array of frequencies
    in a tone block), we always start at at the *first* sample.
    '''
    return linspace(fs**-1, duration, fs*duration)

def convert(value, src_unit, req_unit):
    '''
    Convert value to desired unit.

    Parameters
    ----------
    value : number
        value to be converted
    src_unit : string
        unit of value
    req_unit : string
        unit to convert value to
    
    Right now this is a fairly "dumb" implementation that does not factor in the
    possible need for using other paramters to complete the conversion.  One
    possibility is that the amplitude parameter would need to know the frequency
    of the tone before computing the appropriate conversion to dB SPL.  However,
    it's not clear to me the best approach for handling these "complex"
    conversions, or whether they are best handled elsewhere.

    One use case that would be extremely useful is the ability to convert phase
    to interaural time delay; however this process requires knowledge of the
    *frequency* (plus the width of the gerbil's head).  This is not implemented
    for now.

    Examples
    --------
    >>> convert(2.5, 's', 'ms')
    2500
    >>> convert(1000, 'Hz', 'period')
    0.001
    >>> convert(convert(1000, 'Hz', 'period'), 's', 'ms')
    1.0
    '''
    map = {
        ('s', 'ms')             : lambda s: s*1e3,
        ('s', 'us')             : lambda s: s*1e6,
        ('ms', 's')             : lambda s: s*1e-3,
        ('ms', 'us')            : lambda s: s*1e3,
        ('us', 'ms')            : lambda s: s*1e-3,
        ('us', 's')             : lambda s: s*1e-6,
        ('radians', 'degrees')  : lambda radians: radians/(2.*pi)*360.,
        ('degrees', 'radians')  : lambda degrees: 2.*pi*degrees/360.,
        ('Hz', 'period')        : lambda Hz: Hz**-1,
        ('period', 'Hz')        : lambda period: period**-1,
    }
    try:
        return map[src_unit, req_unit](value)
    except KeyError:
        # Create a more informative error message than KeyError
        raise ValueError('Conversion from %s to %s not supported', 
                         src_unit, req_unit)

################################################################################
# Interface definitions
################################################################################
class Parameter(object):
    '''
    Defines a block parameter

    Properties
    ----------
    default : number
        If no source is provided, default to this value
    valid_bounds : tuple
        Require that value be in the range [lower, upper)
    warn_bounds : tuple
        Warn if value falls outside the range [lower, upper)
    unit : required unit of parameter

    Never rely on the default value when creating paradigms for use in your
    experiments!  I am very likely to change these values as I see fit.
    Default values are primarily for debugging purposes.
    '''

    def __init__(self, default=None, unit=None, valid_bounds=None,
                 warn_bounds=None):
        self.__dict__.update(locals())

    def set(self, value, unit=None):
        if unit is None:
            unit = self.unit
        if not isinstance(value, Modulation):
            value = Constant(value, unit)
        self.source = value

    def get(self, t, fs, clip_value):
        '''
        Get value of parameter

        Parameters
        ----------
        t : array-like
            Time vector
        fs : float
            Sampling frequency
        clip : boolean
            Clip value to valid bounds before returning

        Each block (e.g. :class:`Constant`) does not necessarily need t, fs or
        unit for computing its value; however, this allows a simple way for
        crucial context to propagate to the blocks that need it.
        '''
        try:
            value = self.source.get(t, fs, self.unit)
        except AttributeError:
            value = self.default

        if clip_value and self.valid_bounds is not None:
            lb, ub = self._eval_bounds(self.valid_bounds, fs)
            return clip(value, lb, ub)
        else:
            return value

    def is_valid(self, value, fs):
        '''
        Returns True if value is valid
        '''
        if self.valid_bounds is not None:
            lb, ub = self._eval_bounds(self.valid_bounds, fs)
            return lb <= value < ub
        else:
            return True

    def is_reasonable(self, value, fs):
        '''
        Returns True if value is reasonable
        '''
        if self.warn_bounds is not None:
            lb, ub = self._eval_bounds(self.warn_bounds, fs)
            return lb <= value < ub
        else:
            return True

    def _eval_bounds(self, bounds, fs):
        lb, ub = bounds
        if type(lb) == type(''):
            lb = eval(lb, context)
        if type(ub) == type(''):
            ub = eval(ub, context)
        return lb, ub

    def __repr__(self):
        return repr(self.source)

################################################################################
# Interface definitions
################################################################################
class Block(object):

    def __init__(self, **kw):
        '''
        Parameters must have been defined in advance
        '''
        for k, v in kw.items():
            if type(v) == tuple:
                c, unit = v
                getattr(self, k).set(Constant(c, unit))
            else:
                getattr(self, k).set(v)

    def _get_parameters(self):
        return [v for v in self.__dict__.values() if isinstance(v, Parameter)]

    parameters = property(_get_parameters)

class Carrier(Block):
    '''
    Defines a fundamental signal
    '''
    pass

class Operation(Block):
    '''
    Perform an operation on a realized waveform
    '''

    def min_duration(self):
        '''
        Minimum length (in seconds) required by the operation to avoid boundary
        conditions.
        '''
        raise NotImplementedException

class Modulation(Block):
    '''
    Generate a waveform that is used as a parameter for another block
    '''
    pass

class Experiment(Block):

    waveform        = Parameter()
    trial_dur       = Parameter(1, 's', (0, inf), (0.01, 10))
    trial_env_dur   = Parameter(1, 's', (0, inf), (0.01, 10))
    int_trial_dur   = Parameter(0, 's', (0, inf), (0.01, 10))
    int_set_dur     = Parameter(1, 's', (0, inf), (0, inf))
    trial_reps      = Parameter(1, None, (1, inf), (1, 5))
    set_reps        = Parameter(1, None, (1, inf), (1, inf))

    def realize(self, fs):
        waveform        = self.waveform.get(t, fs)
        trial_dur       = self.trial_dur.get(t, fs)
        trial_env_dur   = self.trial_env_dur.get(t, fs)
        int_trial_dur   = self.int_trial_dur.get(t, fs)
        trial_reps      = self.trial_reps.get(t, fs)
        int_set_dur     = self.int_set_dur.get(t, fs)
        set_reps        = self.set_reps.get(t, fs)

        trial_waveform = cos2taper(waveform, trial_env_dur*fs)
        int_trial_waveform = np.zeros(int_trial_dur*fs)
        int_set_waveform = np.zeros(int_set_dur*fs)

        trial_triggers = []
        set_triggers = []

        # Repeat the trials to form a single set waveform
        set = []
        for i in range(trial_reps):
            trial_triggers.append(len(set))
            set.extend(trial_waveform)
            set.extend(int_trial_waveform)

        # Repeat the set waveform to form the final waveform
        final = []
        for i in range(set_reps):
            n = len(final)
            trial_triggers.extend([t+n for t in trial_triggers[:trial_reps]])
            set_triggers.append(n)
            final.extend(set)
            final.extend(int_set_waveform)

        # Finalize the waveform
        waveform = np.array(final)
        t = np.arange(len(waveform))/fs
        return t, waveform, trial_triggers, set_triggers

    def __repr__(self):
        return "<Experiment>"

################################################################################
# Carrier Blocks
################################################################################
class Tone(Carrier):

    frequency = Parameter(1000, 'Hz', (0, '0.5*fs**-1'), (300, inf))
    amplitude = Parameter(1, 'V', (0, 10), (0.01, 5))
    phase     = Parameter(0, 'radians', None, (0, 2*pi))

    def get(self, t, fs):
        # To modulate frequency, we must transform the instantaneous frequency
        # into the instantaneous phase of the signal.  For a fixed-frequency
        # tone, the phase increases at a constant rate.  We also factor out the
        # time vector since it's put back in during the final step.
        frequency = self.frequency.get(t, fs)
        try:
            frequency = frequency.cumsum()*(fs**-1)/t
        except:
            pass
        amplitude = self.amplitude(t, fs)

        # TODO: Implement special case for phase modulation.  Amplitude
        # modulation should not require any adjustment.  
        phase     = self.phase(t, fs)
        return amplitude*sin(2*pi*frequency*t+phase)

    def __repr__(self):
        return "<Tone Carrier: {0}, {1}, {2}>".format(self.frequency,
                                                      self.amplitude,
                                                      self.phase)

#class FM(Carrier):
#
#    warnings = [
#        ('(fc-fm)>0', '''Selected combination of {fc} and {fm} extends into the
#         negative frequency domain.  Modulation will be clipped to a minimum of
#         1 Hz.'''),
#        ('(fc+fm)<0.5*bandwidth)<500', '''The noise band extends into a frequency
#         region that may be outside the best range of the speaker.'''),
#        ] 
#
#    fc        = Parameter(1000, (0, '0.5*fs**-1'), (300, None), 'Hz', 
#                          'Carrier frequency') 
#    fm        = Parameter(5, (0, '0.5*fs**-1'), 0.1, 50, , 'Hz', 
#                          'Modulation frequency') 
#    pc        = Parameter(-inf, 0, 2*pi, inf, ('radians', 'degrees'),
#                          'Carrier phase')
#    pm        = Parameter(-inf, 0, 2*pi, inf, ('radians', 'degrees'), 
#                          'Modulator phase')
#    amplitude = Parameter(0, 0.01, 5, 10, 'V')
#
#    def __call__(self, t, fs):
#        fm        = self.fm(t, fs, 'Hz')
#        fc        = self.fc(t, fs, 'Hz')
#        amplitude = self.amplitude(t, fs, 'V')
#        phase     = self.phase(t, fs, 'radians')
#        return amplitude*sin(2*pi*fc*t+depth/fm*cos(2*pi*fm*t+pm)+pc)
#
#class Noise(Carrier):
#
#    warnings = [
#        ('(fc-0.5*bandwidth)>0', '''Selected combination of {fc} and {bandwidth}
#         extends into the negative frequency domain.  Lower bound of the noise
#         band will be clipped to zero.'''),
#        ('(fc-0.5*bandwidth)<500', '''The noise band extends into a frequency
#         region that may be outside the best range of the speaker.'''),
#        ('(fc+0.5*bandwidth)<(0.5*fs**-1', '''The noise band extends into a
#         frequency region that is greater than the Nyquist frequency.  The noise
#         band will be clipped to {0.5*fs**-1} Hz.'''),
#        ] 
#
#    fc        = Parameter(0, 300, None, '0.5*fs**-1', 'Hz', 'carrier frequency') 
#    bandwidth = Parameter(0, 1, None, '0.25*fs**-1', 'Hz')
#    seed      = Parameter()
#    amplitude = Parameter(0, 0.01, 5, 10, 'V')
#
#    def __call__(self, t, fs):
#        fc        = self.fc(t, fs, 'Hz')
#        bandwidth = self.bandwidth(t, fs, 'Hz')
#        seed      = self.seed(t, fs)
#        amplitude = self.amplitude(t, fs, 'V')
#
#        #random.seed(seed)
#        noise = random.uniform(low=-1, high=1, size=len(t))
#        fl = fc-bandwidth
#        fh = fc+bandwidth
#        Wn = divide([fl, fh], fs/2.)
#        b, a = signal.iirfilter(8, Wn)
#        return signal.filtfilt(b, a, amplitude*noise)
#
################################################################################
# Operation Blocks
################################################################################
class Constant(Operation):
    '''
    Note that in general this block should be implied (i.e. we should not be
    required to wire this block to each parameter to set their value.  However,
    this is a block that can be placed on the flowchart if desired.  This is
    useful for cases where we need to ensure two parameters are equal (by
    directly linking this block to the parameters) or enforce a mathematical
    relationship between several parameters (via an eval operation).
    '''

    def __init__(self, value, unit):
        self.__dict__.update(locals())

    def get(self, t, fs, unit):
        if unit != self.unit:
            return convert(self.value, self.unit, unit)
        else:
            return self.value

    def __repr__(self):
        return '<Constant: {0} {1}>'.format(self.value, self.unit)

class Sinusoid(Operation):
    pass

class Trapezoid(Operation):
    pass

class Triangle(Trapezoid):
    pass

################################################################################
# Demo functions
################################################################################
def test_tone():
    fs = 1e3
    ts = t(fs, 10)
    tone = Tone(frequency=1, amplitude=1, phase=0)
    signal = tone(ts, fs)
    from pylab import plot, show
    plot(ts, signal)
    show() 
################################################################################
# Demo Flowcharts
################################################################################
tone_pip = {
    'trial_dur'     : 1,
    'trial_env_dur' : 0.25,
    'int_trial_dur' : 0,
    'trial_reps'    : 1,
    'int_set_dur'   : 1,
    'set_reps'      : 1,
    'waveform'      : (Tone, {
                       'frequency'   : .25e3,
                       'amplitude'   : 1,
                       'phase'       : 0, 
                       }),
    }

def prepare_experiment(parameters):

    def parse_args(parameters):
        result = {}
        for par, value in parameters.items():
            if type(value) == tuple and issubclass(value[0], Block):
                klass, args = value
                parsed = parse_args(args)
                result[par] = klass(**parsed)
            else:
                result[par] = value
        return result

    return Experiment(**parse_args(parameters))

def test_noise():
    waveform = Noise(fc=5000, bandwidth=1000, seed=1, amplitude=1)
    fs = 20e3
    ts = t(fs, 1)
    from pylab import plot, show
    plot(ts, waveform(ts, fs))
    show()
    #Experiment(trial_dur=1, trial_env_dur=0.25, int_trial_dur=0.5, trial_reps=3,
    #           int_set_dur=5, set_reps=2, waveform=)

if __name__ == '__main__':
    #test_noise()
    exp = prepare_experiment(tone_pip)
    print exp.waveform.source

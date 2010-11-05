#__all__ = [ Tone, Noise, FM ]

from scipy import signal
from numpy import inf, nan, pi, sin, cos, divide, random, linspace, ones

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
    possible need for using other paramters to cmplete the conversion.  However,
    it's not clear to me this is a valid use case at the moment.  We will not
    put any effort into implementing it.

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
        raise ValueError('Conversion from %s to %s not supported', src_unit,
                         req_unit)

################################################################################
# Interface definitions
################################################################################
class Parameter(object):
    '''
    Defines a block parameter

    Properties
    ----------
    valid_bounds : tuple
        Require that value be in the range [lower, upper)
    warn_bounds : tuple
        Warn if value falls outside the range [lower, upper)
    units : string or list of strings
        Valid units for the parameter, first in sequence is the default
    '''
    # TODO: Needs a bit mor ethinking through

    def __init__(self, source, default, valid_bounds, warn_bounds, units=None):
        if type(units) == str:
            units = (units,)
        if units is not None:
            default_unit = units[0]
        else:
            default_unit = None

        self.__dict__.update(locals())

    def set(self, value, unit=None):
        # TODO: is this a good time to check if this is a valid parameter?
        self.value = value
        if unit is None:
            self.unit = self.default_unit

    def get(self, unit):
        # TODO: how do we factor in conversions that depend on other parameters?
        if unit != self.unit:
            return convert(self.value, self.unit, unit)
        else:
            return self.value

    def __call__(self, t, fs, unit=None):
        #return ones(len(t))*self.get(unit)
        return self.get(unit)

    def validate(self, fs):
        '''
        Given the samping frequency, ensure that the parameter is valid.
        '''
        # TODO: we may need to consider fleshing out the context to include
        # additional edge cases; however, I think fs is the only special case
        # right now that we need.
        context = {'fs': fs}
        lb, ub = self.valid_bounds
        if type(lb) == type(''):
            lb = eval(lb, context)
        if type(ub) == type(''):
            ub = eval(ub, context)

        raise NotImplementedException

    def warn(self, fs):
        raise NotImplementedException

################################################################################
# Interface definitions
################################################################################
class Block(object):
    # TODO: add validation and warning checks of parameters

    def _get_parameters(self):
        return [v for v in self.__dict__.values() if isinstance(v, Parameter)]

    parameters = Property(_get_parameters)

    def validate(self):
        for p in self.parameters:


    def __init__(self, **kw):
        '''
        Parameters must have been defined in advance
        '''
        # TODO: is this a good way to handle setting the unit: e.g. a tuple
        # (value, unit).  Overall the Paramter system seems a bit hackish, but I
        # think it sets a good framework that we can rethink without changing
        # too much.
        for k, v in kw.items():
            if type(v) == tuple:
                getattr(self, k).set(v[0], unit=v[1])
            elif isinstance(v, Block):
                setattr(self, k, v)
            else:
                getattr(self, k).set(v)

    def validate(self):
        raise NotImplementedException

class Carrier(Block):
    '''
    Defines a fundamental signal
    '''

    def realize(self, fs):
        '''
        Generate waveform
        '''
        raise NotImplementedException

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

    def apply(self, *waveforms):
        '''
        Perform operation
        '''
        raise NotImplementedException

class Modulation(Block):
    '''
    Generate a waveform that is used as a parameter for another block
    '''
    def realize(self, fs):
        '''
        Generate waveform
        '''
        raise NotImplementedException

class Experiment(Block):

    waveform        = Parameter()
    trial_dur       = Parameter()
    trial_env_dur   = Parameter()
    int_trial_dur   = Parameter()
    trial_reps      = Parameter()
    int_set_dur     = Parameter()
    set_reps        = Parameter()

    def __call__(self, t, fs):
        waveform        = self.waveform(t, fs)
        trial_dur       = self.trial_dur(t, fs)
        trial_env_dur   = self.trial_env_dur(t, fs)
        int_trial_dur   = self.int_trial_dur(t, fs)
        trial_reps      = self.trial_reps(t, fs)
        int_set_dur     = self.int_set_dur(t, fs)
        set_reps        = self.set_reps(t, fs)

        # Note that the waveform simply reflects the *envelope* of the trial
        # waveform.  It does not represent the *actual* trial waveform itself.
        # The trial waveform may be more nuanced than this.
        trial_waveform = cos2taper(waveform, trial_env_dur*fs)
        int_trial_waveform = np.zeros(int_trial_dur*fs)
        int_set_waveform = np.zeros(int_set_dur*fs)

        trial_triggers = []
        set_triggers = []

        set = []
        for i in range(trial_reps):
            trial_triggers.append(len(set))
            set.extend(trial_waveform)
            set.extend(int_trial_waveform)

        final = []
        for i in range(set_reps):
            n = len(final)
            trial_triggers.extend([t+n for t in trial_triggers[:trial_reps]])
            set_triggers.append(n)inf
            final.extend(set)
            final.extend(int_set_waveform)

        waveform = np.array(final)
        t = np.arange(len(waveform))/fs
        return t, waveform, trial_triggers, set_triggers

################################################################################
# Carrier Blocks
################################################################################
class Tone(Carrier):

    frequency = Parameter(1000, (0, '0.5*fs**-1'), (300, None), 'Hz') 
    amplitude = Parameter(1, (0, 10), (0.01, 5), 'V')
    phase     = Parameter(0, (-inf, inf), (0, 2*pi), ('radians', 'degrees'))

    warnings  = []
    errors    = []

    def __call__(self, t, fs):
        # To modulate frequency, we must transform the instantaneous frequency
        # into the instantaneous phase of the signal.  For a fixed-frequency tone,
        # the phase increases at a constant rate. Of note, the integral of an
        # array The instantaneous phase of a modulated waveform can be computed by
        # the integral.  We need to factor out the time domain as well.
        frequency = self.frequency(t, fs, 'Hz').cumsum()*(fs**-1)/t
        amplitude = self.amplitude(t, fs, 'V')
        # TODO: Implement special case for phase modulation.  Amplitude
        # modulation should not require any adjustment.  
        phase     = self.phase(t, fs, 'radians')
        return amplitude*sin(2*pi*frequency*t+phase)

class FM(Carrier):

    warnings = [
        ('(fc-fm)>0', '''Selected combination of {fc} and {fm} extends into the
         negative frequency domain.  Modulation will be clipped to a minimum of
         1 Hz.'''),
        ('(fc+fm)<0.5*bandwidth)<500', '''The noise band extends into a frequency
         region that may be outside the best range of the speaker.'''),
        ] 

    fc        = Parameter(0, 300, None, '0.5*fs**-1', 'Hz', 'Carrier frequency') 
    fm        = Parameter(0, 0.1, 50, '0.5*fs**-1', 'Hz', 
                          'Modulation frequency') 
    pc        = Parameter(-inf, 0, 2*pi, inf, ('radians', 'degrees'),
                          'Carrier phase')
    pm        = Parameter(-inf, 0, 2*pi, inf, ('radians', 'degrees'), 
                          'Modulator phase')
    amplitude = Parameter(0, 0.01, 5, 10, 'V')

    def __call__(self, t, fs):
        fm        = self.fm(t, fs, 'Hz')
        fc        = self.fc(t, fs, 'Hz')
        amplitude = self.amplitude(t, fs, 'V')
        phase     = self.phase(t, fs, 'radians')
        return amplitude*sin(2*pi*fc*t+depth/fm*cos(2*pi*fm*t+pm)+pc)

class Noise(Carrier):

    warnings = [
        ('(fc-0.5*bandwidth)>0', '''Selected combination of {fc} and {bandwidth}
         extends into the negative frequency domain.  Lower bound of the noise
         band will be clipped to zero.'''),
        ('(fc-0.5*bandwidth)<500', '''The noise band extends into a frequency
         region that may be outside the best range of the speaker.'''),
        ('(fc+0.5*bandwidth)<(0.5*fs**-1', '''The noise band extends into a
         frequency region that is greater than the Nyquist frequency.  The noise
         band will be clipped to {0.5*fs**-1} Hz.'''),
        ] 

    fc        = Parameter(0, 300, None, '0.5*fs**-1', 'Hz', 'carrier frequency') 
    bandwidth = Parameter(0, 1, None, '0.25*fs**-1', 'Hz')
    seed      = Parameter()
    amplitude = Parameter(0, 0.01, 5, 10, 'V')

    def __call__(self, t, fs):
        fc        = self.fc(t, fs, 'Hz')
        bandwidth = self.bandwidth(t, fs, 'Hz')
        seed      = self.seed(t, fs)
        amplitude = self.amplitude(t, fs, 'V')

        #random.seed(seed)
        noise = random.uniform(low=-1, high=1, size=len(t))
        fl = fc-bandwidth
        fh = fc+bandwidth
        Wn = divide([fl, fh], fs/2.)
        b, a = signal.iirfilter(8, Wn)
        return signal.filtfilt(b, a, amplitude*noise)

################################################################################
# Operation Blocks
################################################################################
class Constant(Operation):
    '''
    Note that in general this block should be implied (i.e. we should not be
    required to wire this block to each parameter to set their value.  However,
    this is a block that can be placed on the flowchart if desired.  This is
    useful for cases where we need to ensure two parameters are equal (by directly
    linking this block to the parameters) or enforce a mathematical relationship
    between several parameters (via an eval operation).
    '''
    value    = Parameter()

    def __call__(self, t, fS):
        return self.value.get(t, fs)

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
    test_noise()

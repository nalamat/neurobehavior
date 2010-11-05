from __future__ import division
from cns.signal.util import cos2taper
import numpy as np
from pylab import subplot, show, fill_between, title, plot, gcf, axvline, axis
from scipy.signal import iirfilter, filtfilt

fs = 50000 # samples per second

def generate_waveform(waveform, trial_dur, trial_env_dur, int_trial_dur,
                      trial_reps, int_set_dur, set_reps):

    # Note that the waveform simply reflects the *envelope* of the trial
    # waveform.  It does not represent the *actual* trial waveform itself.  The
    # trial waveform may be more nuanced than this.

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
        set_triggers.append(n)
        final.extend(set)
        final.extend(int_set_waveform)

    waveform = np.array(final)
    t = np.arange(len(waveform))/fs
    return t, waveform, trial_triggers, set_triggers

demos = [
    dict(trial_dur=1, trial_env_dur=0.25, int_trial_dur=0.5, trial_reps=3,
         int_set_dur=5, set_reps=2),
    dict(trial_dur=1, trial_env_dur=0.25, int_trial_dur=0, trial_reps=1,
         int_set_dur=3, set_reps=3),
    dict(trial_dur=1, trial_env_dur=0.25, int_trial_dur=3, trial_reps=3,
         int_set_dur=0, set_reps=1),
    dict(trial_dur=2, trial_env_dur=0.5, int_trial_dur=0, trial_reps=4,
         int_set_dur=1, set_reps=2),
    dict(trial_dur=.5, trial_env_dur=0, int_trial_dur=1, trial_reps=5,
         int_set_dur=2, set_reps=3),
    dict(trial_dur=1, trial_env_dur=0, int_trial_dur=0, trial_reps=10,
         int_set_dur=2, set_reps=2),
    dict(trial_dur=10, trial_env_dur=0, int_trial_dur=0, trial_reps=1,
         int_set_dur=2, set_reps=2),
    ]

def demo_envelopes():

    for i, demo in enumerate(demos):
        try:
            prev = subplot(len(demos), 1, i+1, sharex=prev, sharey=prev)
        except NameError:
            prev = subplot(len(demos), 1, i+1)
        title(repr(demo).strip('{}').replace("'", ""))
        prev.yaxis.set_visible(False)
        prev.xaxis.set_visible(False)

        # Generate carrier of appropriate length for the trial
        #carrier = np.random.normal(size=demo['trial_dur']*fs)
        carrier = np.random.uniform(low=-1, high=1, size=demo['trial_dur']*fs)
        t, waveform, trial_trigs, set_trigs = generate_waveform(carrier, **demo)
        #fill_between(t, waveform, -waveform)
        plot(t, waveform, 'k')
        for trig in set_trigs:
            axvline(trig/fs, color='b', lw=5)
        #for trig in trial_trigs:
        #    axvline(trig/fs, color='b', lw=2.5)
        trig_times = np.true_divide(trial_trigs, fs)
        plot(trig_times, np.ones(len(trig_times)), 'ro')
    prev.xaxis.set_visible(True)
    gcf().subplots_adjust(left=0.05, right=0.95, bottom=0.05, top=0.95,
                          hspace=0.5)
    axis(xmin=-1, ymin=-1.1, ymax=1.1)
    show()

def cos2ramp(n):
    return np.sin(np.linspace(0, np.pi / 2., n)) ** 2

def cosramp(n):
    return np.sin(np.linspace(0, np.pi / 2., n))

def linramp(n):
    return np.arange(n, dtype='f') / n

def env(n, ramp):
    return np.r_[ramp, np.ones(n-2*len(ramp)), ramp[::-1]]

def sin_mod(t, offset, depth, frequency, phase):
    return depth*np.sin(2*np.pi*frequency*t+phase)+offset

#def fm(t, amplitude, fc, depth, pc, fm, pm):
#    return amplitude*np.sin(2*np.pi*fc*t+depth/fm*np.cos(2*np.pi*fm*t+pm)+pc)

#def tone(t, amplitude, frequency, phase):
#    try:
#        frequency = frequency.cumsum()*(fs**-1)/t
#    except:
#        pass
#    return amplitude*np.sin(2*np.pi*frequency*t+phase)

def assert

def sin_mod_op(t, waveform, frequency, phase, depth):
    mod_wave = depth/2.*np.sin(2*np.pi*frequency*t+phase)+depth/2.
    return mod_wave*waveform

def noise(t, amplitude, center_frequency, bandwidth):
    noise = np.random.uniform(low=-1, high=1, size=len(t))
    fl = center_frequency-bandwidth
    fh = center_frequency+bandwidth
    Wn = np.divide([fl, fh], fs/2.)
    b, a = iirfilter(8, Wn)
    return filtfilt(b, a, amplitude*noise)

def cos2env(waveform, ramp_dur, env_dur):
    ramp(env_dur*fs, cos2ramp(ramp_dur*fs))
    #np.zeros(ramp_dur*fs

def add(*waveforms):
    return np.c_[waveforms].sum(axis=1)

class Delay(Block):

    def __init__(self, duration):

    def duration(

def delay(waveform, dur):
    n = dur*fs
    zeros = np.zeros(dur*fs)
    return np.r_[zeros, waveform[n:]]

blocks = {
    'tone': tone,
    'sin_mod': sin_mod,
    'noise': noise,
    'sin_mod_op': sin_mod_op,
    'fm': fm,
}

flowcharts = [
    { # Flowchart 1
    'trial_dur': 1,
    'trial_env_dur': 0.25,
    'int_trial_dur': 0,
    'trial_reps': 1,
    'int_set_dur': 1,
    'set_reps': 1,
    'waveform': ('tone', 
                 {'frequency': .25e3,
                  'amplitude': 1,
                  'phase': 0, 
                 }),
    },
    { # Flowchart 2
    'trial_dur': 1,
    'trial_env_dur': 0,
    'int_trial_dur': 0,
    'trial_reps': 1,
    'int_set_dur': 1,
    'set_reps': 1,
    'waveform': ('sin_mod_op', 
                 {'frequency': 5,
                  'depth': 1,
                  'phase': 0,
                  'waveform': ('noise', 
                               {'center_frequency': 5000,
                                'bandwidth': 1000,
                                'amplitude': 1,
                               }),
                 }),
    },
    { # Flowchart 3
    'trial_dur': 1,
    'trial_env_dur': 0,
    'int_trial_dur': 0,
    'trial_reps': 1,
    'int_set_dur': 1,
    'set_reps': 1,
    'waveform': ('tone', 
                 {'frequency': ('sin_mod',
                                {'offset': 1000,
                                 'frequency': 5,
                                 'phase': 0,
                                 'depth': 750,
                                }),
                  'amplitude': 1,
                  'phase': 0,
                 }),
    },
    #{ # Flowchart 4
    #'trial_dur': 1,
    #'trial_env_dur': 0,
    #'int_trial_dur': 0,
    #'trial_reps': 1,
    #'int_set_dur': 1,
    #'set_reps': 1,
    #'waveform': ('fm', 
    #             {'amplitude': 1,
    #              'fc': 1000,
    #              'depth': 750,
    #              'pc': 0,
    #              'fm': 5,
    #              'pm': 0,
    #             }),
    #},
    { # Flowchart 4
    'trial_dur': 1,
    'trial_env_dur': 0,
    'int_trial_dur': 0,
    'trial_reps': 1,
    'int_set_dur': 1,
    'set_reps': 1,
    'waveform': ('fm', 
                 {'amplitude': 1,
                  'fc': 1000,
                  'depth': 750,
                  'pc': 0,
                  'fm': 5,
                  'pm': 0,
                 }),
    },
]

def demo_token():

    def parse_args(t, parameters):
        for k, v in parameters.items():
            if type(v) == tuple:
                name, args = v
                parse_args(t, args)
                parameters[k] = blocks[name](t, **args)

    for i, params in enumerate(flowcharts):
        try:
            prev = subplot(len(flowcharts), 1, i+1, sharex=prev, sharey=prev)
        except NameError:
            prev = subplot(len(flowcharts), 1, i+1)
        #title(repr(flowcharts).strip('{}').replace("'", ""))
        prev.yaxis.set_visible(False)
        prev.xaxis.set_visible(False)

        #t = np.arange(params['trial_dur']*fs, dtype='f')/fs
        t = np.linspace(fs**-1, params['trial_dur'], fs*params['trial_dur'])
        parse_args(t, params)
        t, waveform, trial_trigs, set_trigs = generate_waveform(**params)
        plot(t, waveform)
    
    show()

demo_envelopes()
#demo_token()


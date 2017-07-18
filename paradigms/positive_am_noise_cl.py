'''
Appetitive AM noise
-------------------
:Authors:   Brad Buran <bburan@alum.mit.edu>
            Gardiner von Trapp <gvontrapp@cns.nyu.edu>

Presents band-limited AM noise tokens that have been tapered with a cos2 ramp.
To minimize onset transients interfering with detection of the sinusoidal
modulation, the modulation onset can be delayed relative to the start of the
token.  

Bandpass noise is generated by drawing samples from a uniform distribution (-1
to 1) and band-pass filtering this using a Chebyshev filter.  Settings for the
Chebyshev filter are defined via the parameters below.  The band-pass filtered
noise is renormalized to a RMS of 1.

Available parameters
....................
level : float (dB SPL)
    Desired spectrum level
modulation_onset : float (seconds)
    Time (re start of token) before sinusoidal modulation begins 
fm : float (Hz)
    Modulation frequency
modulation_depth : float in range [0, 1]
    Depth of modulation (as a fraction)
modulation_direction : {'positive', 'negative'}
    Initial direction of modulation if starting phase is nonzero.
duration : float (seconds)
    Duration of full token (including onset/offset ramps)
rise_fall_time : float (seconds)
    Duration of cosine squared onset/offset ramp
seed : integer
    Seed to use for noise token.  Set the seed to a positive integer for
    "frozen" noise.  If you want a random seed on each token, you must use an
    expression.  To sample from the full range of possible integers (the maximum
    value for a 32-bit signed integer is `2**31-1`), the appropriate expression
    would be `randint(1, 2**31-1)`.  Alternatively, the expression
    `int(time()*1e3)` would give you random seeds based on the system clock.
fc : float (Hz)
    Center frequency of noise band
bandwidth : float (Hz)
    Bandwidth of noise band.  Noise band will run from fc-bw/2 to fc+bw/2.
rs : float (dB)
    Minimum attenuation in stop band.  Used for computing bandpass filter
    coefficients.
rp : float (dB)
    Maximum ripple in pas band (dB)
order : integer
    Filter order.  Note that the order is effectively doubled because we perform
    forward and reverse filtering to eliminate phase delay.
'''

from traits.api import Instance
from traitsui.api import View, Include, VGroup

from ._positive_am_noise_paradigm_mixin import PositiveAMNoiseParadigmMixin
from ._positive_am_noise_controller_mixin import PositiveAMNoiseControllerMixin

from experiments.abstract_positive_experiment_v3 import AbstractPositiveExperiment
from experiments.abstract_positive_controller_v3 import AbstractPositiveController
from experiments.abstract_positive_paradigm_v3 import AbstractPositiveParadigm
from experiments.positive_data_v3 import PositiveData

from experiments.cl_controller_mixin import CLControllerMixin
from experiments.cl_paradigm_mixin import CLParadigmMixin
from experiments.cl_experiment_mixin import CLExperimentMixin
from experiments.positive_cl_data_mixin import PositiveCLDataMixin

from experiments.pump_controller_mixin import PumpControllerMixin
from experiments.pump_paradigm_mixin import PumpParadigmMixin
from experiments.pump_data_mixin import PumpDataMixin

class Controller(
        PositiveAMNoiseControllerMixin,
        AbstractPositiveController, 
        CLControllerMixin,
        PumpControllerMixin):
    pass

class Paradigm(
        PositiveAMNoiseParadigmMixin,
        AbstractPositiveParadigm, 
        PumpParadigmMixin,
        CLParadigmMixin,
        ):

    traits_view = View(
            VGroup(
                Include('constant_limits_paradigm_mixin_group'),
                Include('abstract_positive_paradigm_group'),
                Include('pump_paradigm_mixin_syringe_group'),
                label='Paradigm',
                ),
            VGroup(
                Include('speaker_group'),
                Include('signal_group'),
                label='Sound',
                ),
            )

class Data(
    PositiveData, 
    PositiveCLDataMixin, 
    PumpDataMixin): 
        pass

class Experiment(AbstractPositiveExperiment, CLExperimentMixin):

    data = Instance(Data, ())
    paradigm = Instance(Paradigm, ())

node_name = 'PositiveAMNoiseCLExperiment'

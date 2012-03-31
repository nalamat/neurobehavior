'''
Appetitive temporal integration (constant limits)
-------------------------------------------------
:Author: **Brad Buran <bburan@alum.mit.edu>**
:Method: Constant limits go-nogo
:Status: Stable.  Has been tested and used extensively for several months.

Available parameters
....................
fc : Hz
    Center frequency (Hz).  Will be coerced to the nearest frequency for
    which calibration data is available.  Assumes that the frequency of
level : db SPL
    Level of tone
duration : seconds
    Duration of tone (from ramp onset to ramp offset)
rise_fall_time : seconds 
    Rise/fall time of cos^2 envelope 

'''
from enthought.traits.api import Instance
from enthought.traits.ui.api import View, Include, VGroup

# The underscore indicates that these are not meant to be used directly as an
# experiment paradigm
from ._positive_dt_controller_mixin import DTControllerMixin
from ._positive_dt_paradigm_mixin import DTParadigmMixin

from experiments.abstract_positive_experiment_v2 import AbstractPositiveExperiment
from experiments.abstract_positive_controller_v2 import AbstractPositiveController
from experiments.abstract_positive_paradigm_v2 import AbstractPositiveParadigm
from experiments.positive_data_v2 import PositiveData

from experiments.cl_controller_mixin import CLControllerMixin
from experiments.cl_paradigm_mixin import CLParadigmMixin
from experiments.cl_experiment_mixin import CLExperimentMixin
from experiments.positive_cl_data_mixin import PositiveCLDataMixin

from experiments.pump_controller_mixin import PumpControllerMixin
from experiments.pump_paradigm_mixin import PumpParadigmMixin
from experiments.pump_data_mixin import PumpDataMixin

class Controller(
        # Note that the order of the superclasses are important here.  Both
        # PositiveDTControllerMixin and AbstractPositiveController define the
        # compute_waveform method.  When Python looks for the method, it will
        # work its way through the list of superclasses until it finds a
        # compute_waveform method.  We want to make sure that it finds the one
        # defined in PositiveDTControllerMixin first!
        DTControllerMixin,
        AbstractPositiveController, 
        CLControllerMixin,
        PumpControllerMixin,
        ):
    pass

class Paradigm(
        DTParadigmMixin,
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
                Include('dt_group'),
                label='Sound',
                ),
            )

class Data(PositiveData, PositiveCLDataMixin, PumpDataMixin): pass

class Experiment(AbstractPositiveExperiment, CLExperimentMixin):

    data = Instance(Data, ())
    paradigm = Instance(Paradigm, ())

node_name = 'PositiveDTCLExperiment'

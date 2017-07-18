'''
..module:: paradigms.positive_am_noise_ML
    :platform: Windows
    :synopsis: Appetitive AM noise paradigm

.. moduleauthor:: Brad Buran <bburan@alum.mit.edu>
.. moduleauthor:: Gardiner von Trapp <gvontrapp@cns.nyu.edu>

Presents band-limited AM noise tokens that have been tapered with a cos2 ramp.
To minimize onset transients, the modulation onset can be delayed. 
'''

from traits.api import Instance
from traitsui.api import View, Include, VGroup, Include

from ._positive_am_noise_paradigm_mixin import PositiveAMNoiseParadigmMixin
from ._positive_am_noise_controller_mixin import PositiveAMNoiseControllerMixin

from experiments.abstract_positive_experiment_v3 import AbstractPositiveExperiment
from experiments.abstract_positive_controller_v3 import AbstractPositiveController
from experiments.abstract_positive_paradigm_v3 import AbstractPositiveParadigm
from experiments.positive_data_v3 import PositiveData

from experiments.ml_controller_mixin import MLControllerMixin
from experiments.ml_paradigm_mixin import MLParadigmMixin
from experiments.ml_experiment_mixin import MLExperimentMixin
from experiments.ml_data_mixin import MLDataMixin

from experiments.pump_controller_mixin import PumpControllerMixin
from experiments.pump_paradigm_mixin import PumpParadigmMixin
from experiments.pump_data_mixin import PumpDataMixin

class Controller(
        PositiveAMNoiseControllerMixin,
        AbstractPositiveController, 
        MLControllerMixin,
        PumpControllerMixin):
    pass

class Paradigm(
        PositiveAMNoiseParadigmMixin,
        AbstractPositiveParadigm, 
        PumpParadigmMixin,
        MLParadigmMixin,
        ):

    traits_view = View(
        Include('maximum_likelihood_paradigm_mixin_group'),
        VGroup(
            Include('abstract_positive_paradigm_group'),
            Include('pump_paradigm_mixin_syringe_group'),
            label='Paradigm'
        ),
        VGroup(
            Include('speaker_group'),
            Include('signal_group'),
            label='Sound',
            ),
        )

class Data(
    PositiveData, 
    MLDataMixin, 
    PumpDataMixin): 
        pass

class Experiment(AbstractPositiveExperiment, MLExperimentMixin):

    data = Instance(Data, ())
    paradigm = Instance(Paradigm, ())

node_name = 'PositiveAMNoiseMLExperiment'

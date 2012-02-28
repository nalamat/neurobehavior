from enthought.traits.api import Instance
from enthought.traits.ui.api import View, Include, VGroup

from ._positive_am_noise_paradigm_mixin import PositiveAMNoiseParadigmMixin
from ._positive_am_noise_controller_mixin import PositiveAMNoiseControllerMixin

from experiments import (
        # Controller and mixins
        AbstractPositiveController,
        ConstantLimitsControllerMixin, 
        PumpControllerMixin,

        # Paradigm and mixins
        AbstractPositiveParadigm,
        ConstantLimitsParadigmMixin,
        PumpParadigmMixin,

        # The experiment
        AbstractPositiveExperiment,
        ConstantLimitsExperimentMixin,

        # Data
        PositiveData,
        PositiveConstantLimitsDataMixin
        )

class Controller(
        AbstractPositiveController, 
        ConstantLimitsControllerMixin,
        PumpControllerMixin,
        PositiveAMNoiseControllerMixin):
    pass

class Paradigm(
        AbstractPositiveParadigm, 
        PumpParadigmMixin,
        ConstantLimitsParadigmMixin,
        PositiveAMNoiseParadigmMixin,
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

class Data(PositiveData, PositiveConstantLimitsDataMixin): pass

class Experiment(AbstractPositiveExperiment, ConstantLimitsExperimentMixin):

    data = Instance(Data, (), store='child')
    paradigm = Instance(Paradigm, (), store='child')

node_name = 'PositiveAMNoiseCLExperiment'

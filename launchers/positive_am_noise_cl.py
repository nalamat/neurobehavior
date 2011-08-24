from enthought.traits.api import Instance
from enthought.traits.ui.api import View, Include, VSplit, VGroup, Item
from enthought.enable.api import Component, ComponentEditor

from experiments import (
        # Controller and mixins
        AbstractPositiveController,
        ConstantLimitsControllerMixin, 
        PumpControllerMixin,
        PositiveAMNoiseControllerMixin,

        # Paradigm and mixins
        AbstractPositiveParadigm,
        ConstantLimitsParadigmMixin,
        PumpParadigmMixin,
        AMNoiseParadigmMixin,

        # The experiment
        AbstractPositiveExperiment,
        ConstantLimitsExperimentMixin,

        # Data
        PositiveData,
        ConstantLimitsDataMixin
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
        AMNoiseParadigmMixin,
        ):

    traits_view = View(
            Include('constant_limits_paradigm_mixin_group'),
            Include('abstract_positive_paradigm_group'),
            Include('speaker_group'),
            Include('am_noise_group'),
            Include('pump_paradigm_mixin_syringe_group'),
            )

class Data(PositiveData, ConstantLimitsDataMixin):
    pass

class Experiment(AbstractPositiveExperiment, ConstantLimitsExperimentMixin):

    data = Instance(Data, (), store='child')
    paradigm = Instance(Paradigm, (), store='child')

    traits_view = View(
            Include('traits_group'),
            resizable=True,
            height=0.9,
            width=0.9,
            handler=Controller)

node_name = 'PositiveAMNoiseCLExperiment'

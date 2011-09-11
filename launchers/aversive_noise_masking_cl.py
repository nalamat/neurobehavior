from enthought.traits.api import Instance
from enthought.traits.ui.api import View, Include, VSplit, VGroup, Item
from enthought.enable.api import Component, ComponentEditor
from experiments.evaluate import Expression

from experiments import (
        # Controller and mixins
        AbstractAversiveController,
        ConstantLimitsControllerMixin, 
        PumpControllerMixin,
        AversiveNoiseMaskingControllerMixin,

        # Paradigm and mixins
        AbstractAversiveParadigm,
        ConstantLimitsParadigmMixin,
        PumpParadigmMixin,
        NoiseMaskingParadigmMixin,

        # The experiment
        AbstractAversiveExperiment,
        ConstantLimitsExperimentMixin,

        # Data
        AversiveData,
        AversiveConstantLimitsDataMixin
        )

class Controller(
        AversiveNoiseMaskingControllerMixin,
        ConstantLimitsControllerMixin,
        PumpControllerMixin,
        AbstractAversiveController):
    pass

class Paradigm(
        AbstractAversiveParadigm, 
        PumpParadigmMixin,
        ConstantLimitsParadigmMixin,
        NoiseMaskingParadigmMixin,
        ):

    traits_view = View(
            Include('constant_limits_paradigm_mixin_group'),
            Include('signal_group'),
            Include('abstract_aversive_paradigm_group'),
            Include('pump_paradigm_mixin_syringe_group'),
            Include('speaker_group'),
            )

class Data(AversiveData, AversiveConstantLimitsDataMixin):
    pass

class Experiment(AbstractAversiveExperiment, ConstantLimitsExperimentMixin):

    data = Instance(Data, (), store='child')
    paradigm = Instance(Paradigm, (), store='child')

    traits_view = View(
            Include('traits_group'),
            resizable=True,
            height=0.9,
            width=0.9,
            handler=Controller)

node_name = 'AversiveFMCLExperiment'

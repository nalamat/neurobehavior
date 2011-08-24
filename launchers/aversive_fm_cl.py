from enthought.traits.api import Instance
from enthought.traits.ui.api import View, Include, VSplit, VGroup, Item
from enthought.enable.api import Component, ComponentEditor

from experiments import (
        # Controller and mixins
        AbstractAversiveController,
        ConstantLimitsControllerMixin, 
        PumpControllerMixin,
        AversiveFMControllerMixin,

        # Paradigm and mixins
        AbstractAversiveParadigm,
        ConstantLimitsParadigmMixin,
        PumpParadigmMixin,
        AversiveFMParadigmMixin,

        # The experiment
        AbstractAversiveExperiment,
        ConstantLimitsExperimentMixin,

        # Data
        AversiveData,
        ConstantLimitsDataMixin
        )

class Controller(
        AbstractAversiveController, 
        ConstantLimitsControllerMixin,
        PumpControllerMixin,
        AversiveFMControllerMixin):
    pass

class Paradigm(
        AbstractAversiveParadigm, 
        PumpParadigmMixin,
        ConstantLimitsParadigmMixin,
        FMParadigmMixin,
        ):

    traits_view = View(
            Include('abstract_aversive_paradigm_group'),
            Include('speaker_group'),
            Include('fm_group'),
            Include('pump_paradigm_mixin_syringe_group'),
            )

class Data(AversiveData, ConstantLimitsDataMixin):
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

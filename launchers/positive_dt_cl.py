from enthought.traits.api import Instance
from enthought.traits.ui.api import View, Include, VSplit, VGroup, Item
from enthought.enable.api import Component, ComponentEditor

#from cns.widgets.handler import filehandler_menubar
from experiments.paradigm_menu import create_menubar

from experiments import (
        # Controller and mixins
        AbstractPositiveController,
        ConstantLimitsControllerMixin, 
        PumpControllerMixin,
        TemporalIntegrationControllerMixin,

        # Paradigm and mixins
        AbstractPositiveParadigm,
        ConstantLimitsParadigmMixin,
        PumpParadigmMixin,
        TemporalIntegrationParadigmMixin,

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
        TemporalIntegrationControllerMixin):
    pass

class Paradigm(
        AbstractPositiveParadigm, 
        PumpParadigmMixin,
        ConstantLimitsParadigmMixin,
        TemporalIntegrationParadigmMixin,
        ):

    traits_view = View(
            Include('file_group'),
            Include('constant_limits_paradigm_mixin_group'),
            Include('speaker_group'),
            Include('abstract_positive_paradigm_group'),
            Include('temporal_integration_group'),
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
            menubar=create_menubar(),
            handler=Controller)

node_name = 'PositiveDTCLExperiment'

from enthought.traits.api import Instance
from enthought.traits.ui.api import View, Include, VSplit, VGroup, Item, Include
from enthought.enable.api import Component, ComponentEditor
from experiments.evaluate import Expression

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
        FMParadigmMixin,

        # The experiment
        AbstractAversiveExperiment,
        ConstantLimitsExperimentMixin,

        # Data
        AversiveData,
        AversiveConstantLimitsDataMixin
        )

class Controller(
        AversiveFMControllerMixin,
        ConstantLimitsControllerMixin,
        PumpControllerMixin,
        AbstractAversiveController):

    def initial_setting(self):
        return self.nogo_setting()

class Paradigm(
        AbstractAversiveParadigm, 
        PumpParadigmMixin,
        ConstantLimitsParadigmMixin,
        FMParadigmMixin,
        ):

    editable_nogo = False
    repeat_fa = False
    go_probability = 'h_uniform(c_safe, 3, 7)'

    traits_view = View(
            VGroup(
                VGroup(
                    VGroup(
                        Item('go_probability', label='Warn probability'),
                        Item('go_setting_order', label='Warn setting order'),
                        ),
                    Include('cl_trial_setting_group'),
                    label='Constant limits',
                    show_border=True,
                    ),
                Include('abstract_aversive_paradigm_group'),
                label='Paradigm',
                ),
            VGroup(
                Include('speaker_group'),
                Include('signal_group'),
                label='Signal',
                ),
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

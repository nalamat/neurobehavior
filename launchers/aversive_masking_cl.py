from enthought.traits.api import Instance
from enthought.traits.ui.api import View, Include, VSplit, VGroup, Item
from enthought.enable.api import Component, ComponentEditor
from experiments.evaluate import Expression

from experiments import (
        # Controller and mixins
        AbstractAversiveController,
        ConstantLimitsControllerMixin, 
        PumpControllerMixin,
        AversiveMaskingControllerMixin,

        # Paradigm and mixins
        AbstractAversiveParadigm,
        ConstantLimitsParadigmMixin,
        PumpParadigmMixin,
        MaskingParadigmMixin,

        # The experiment
        AbstractAversiveExperiment,
        ConstantLimitsExperimentMixin,

        # Data
        AversiveData,
        AversiveConstantLimitsDataMixin
        )

class Controller(
        AversiveMaskingControllerMixin,
        ConstantLimitsControllerMixin,
        PumpControllerMixin,
        AbstractAversiveController):
    pass

    def initial_setting(self):
        return self.nogo_setting()

class Paradigm(
        AbstractAversiveParadigm, 
        PumpParadigmMixin,
        ConstantLimitsParadigmMixin,
        MaskingParadigmMixin,
        ):

    #go_probability = 'h_uniform(c_safe, 2, 5)'
    #trial_duration = '0.8'
    #aversive_delay = '0.1+probe_delay+probe_duration'

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

node_name = 'AversiveMaskingExperiment'

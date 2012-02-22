from enthought.traits.api import Instance
from enthought.traits.ui.api import View, Include, VSplit, VGroup, Item
from enthought.enable.api import Component, ComponentEditor

from experiments import (
        # Controller and mixins
        AbstractPositiveController,
        MaximumLikelihoodControllerMixin, 
        PumpControllerMixin,
        TemporalIntegrationControllerMixin,

        # Paradigm and mixins
        AbstractPositiveParadigm,
        MaximumLikelihoodParadigmMixin,
        PumpParadigmMixin,
        TemporalIntegrationParadigmMixin,

        # The experiment object
        AbstractPositiveExperiment,
        MaximumLikelihoodExperimentMixin,

        # Data
        PositiveData,
        MaximumLikelihoodDataMixin
        )

class Controller(
        AbstractPositiveController, 
        MaximumLikelihoodControllerMixin,
        PumpControllerMixin,
        TemporalIntegrationControllerMixin):

    pass

class Paradigm(
        AbstractPositiveParadigm, 
        PumpParadigmMixin,
        MaximumLikelihoodParadigmMixin,
        TemporalIntegrationParadigmMixin,
        ):

    traits_view = View(
            Include('abstract_positive_paradigm_group'),
            Include('maximum_likelihood_paradigm_mixin_group'),
            Include('temporal_integration_group'),
            Include('pump_paradigm_mixin_syringe_group'),
            )

class Data(PositiveData, MaximumLikelihoodDataMixin):
    pass

class Experiment(AbstractPositiveExperiment, MaximumLikelihoodExperimentMixin):

    data = Instance(Data, ())
    paradigm = Instance(Paradigm, ())

    traits_view = View(
            Include('traits_group'),
            resizable=True,
            height=0.9,
            width=0.9,
            handler=Controller)

node_name = 'PositiveDTCLExperiment'

if __name__ == '__main__':
    import tables
    from os.path import join
    from cns import get_config
    filename = join(get_config('TEMP_ROOT'), 'test_experiment.hd5')
    file = tables.openFile(filename, 'w')
    from experiments.trial_setting import add_parameters
    add_parameters(['test'])
    data = Data(store_node=file.root)
    experiment = Experiment(data=data)
    experiment.configure_traits()

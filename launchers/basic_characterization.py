from enthought.traits.api import Instance
from enthought.traits.ui.api import View, Include, VSplit, VGroup, Item
from enthought.enable.api import Component, ComponentEditor

from experiments import (
        # Controller and mixins
        BasicCharacterizationController,
        BasicCharacterizationParadigm,
        AbstractExperiment,
        AbstractExperimentData,
        )

class Controller(BasicCharacterizationController): pass
class Paradigm(BasicCharacterizationParadigm): pass
class Experiment(AbstractExperiment):

    traits_group = VGroup(
            Item('handler.toolbar', style='custom'),
            Item('paradigm', style='custom'),
            show_labels=False,
            )

class Data(AbstractExperimentData): pass

node_name = 'BasicCharacterizationExperiment'

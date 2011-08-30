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
class Experiment(AbstractExperiment): pass
class Data(AbstractExperimentData): pass

node_name = 'BasicCharacterizationExperiment'

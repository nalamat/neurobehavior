from enthought.traits.ui.api import View, Include 
from enthought.traits.api import Instance

from abstract_aversive_experiment import AbstractAversiveExperiment
from aversive_fm_paradigm import AversiveFMParadigm
from aversive_fm_controller import AversiveFMController

class AversiveFMExperiment(AbstractAversiveExperiment):

    paradigm = Instance(AversiveFMParadigm, ())

    traits_view = View(Include('traits_group'),
                       resizable=True,
                       kind='live',
                       handler=AversiveFMController)

from enthought.traits.api import Instance
from enthought.traits.ui.api import View, Include

from abstract_aversive_experiment import AbstractAversiveExperiment
from aversive_am_noise_controller import AversiveAMNoiseController
from aversive_am_noise_paradigm import AversiveAMNoiseParadigm

class AversiveAMNoiseExperiment(AbstractAversiveExperiment):

    paradigm = Instance(AversiveAMNoiseParadigm, ())

    traits_view = View(Include('traits_group'),
                       resizable=True,
                       kind='live',
                       height=0.9,
                       width=0.9,
                       handler=AversiveAMNoiseController)

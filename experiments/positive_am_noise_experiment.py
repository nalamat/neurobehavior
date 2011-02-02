from enthought.traits.api import Instance
from enthought.traits.ui.api import View, Include

from abstract_positive_experiment import AbstractPositiveExperiment
from positive_am_noise_paradigm import PositiveAMNoiseParadigm
from positive_am_noise_controller import PositiveAMNoiseController

class PositiveAMNoiseExperiment(AbstractPositiveExperiment):

    paradigm = Instance(PositiveAMNoiseParadigm, ())

    traits_view = View(Include('traits_group'),
                       resizable=True,
                       kind='live',
                       handler=PositiveAMNoiseController)

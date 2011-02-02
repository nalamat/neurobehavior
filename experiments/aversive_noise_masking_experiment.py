from enthought.traits.api import Instance
from enthought.traits.ui.api import View, Include

from abstract_aversive_experiment import AbstractAversiveExperiment
from aversive_noise_masking_paradigm import AversiveNoiseMaskingParadigm
from aversive_noise_masking_controller import AversiveNoiseMaskingController

class AversiveNoiseMaskingExperiment(AbstractAversiveExperiment):

    # In AbstractAversiveExperiment, paradigm is defined as an instance of
    # AbstractAversiveParadigm.  This subclass redefines paradigm as
    # AversiveNoiseMaskingParadigm rather than AbstractAversiveParadigm.  Thus,
    # when you initialize this subclass, it will create an instance of
    # AversiveNoiseMaskingParadigm by default (rather than an instance of
    # AbstractAversiveParadigm).
    paradigm = Instance(AversiveNoiseMaskingParadigm, ())

    # Redefine the handler to be AversiveNoiseMaskingController rather than the
    # generic AbstractAversiveController.  The view also includes the parameter,
    # traits_group (defined in BaseAversiveParadigm)
    traits_view = View(Include('traits_group'),
                       resizable=True,
                       kind='live',
                       handler=AversiveNoiseMaskingController)

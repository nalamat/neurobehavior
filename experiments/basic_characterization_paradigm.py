from abstract_experiment_paradigm import AbstractExperimentParadigm
from enthought.traits.api import Range
from enthought.traits.ui.api import View, VGroup

class BasicCharacterizationParadigm(AbstractExperimentParadigm):

    token_duration          = Range(0.0, 10.0, 1.0, init=True, immediate=True)
    trial_duration          = Range(0.0, 20.0, 2.0, init=True, immediate=True)

    center_frequency        = Range(0.0, 50e3, 5e3, init=True, immediate=True)
    bandwidth_ratio         = Range(0.0, 16, 0.3, init=True, immediate=True)
    modulation_frequency    = Range(0.0, 100, 5.0, init=True, immediate=True)
    modulation_depth        = Range(0.0, 1.0, 0.0, init=True, immediate=True)

    traits_view = View(
            VGroup(
                'trial_duration',
                'token_duration',
                'center_frequency',
                'bandwidth_ratio',
                'modulation_frequency',
                'modulation_depth'
                ),
            width=400,
            title='Positive paradigm editor',
            )

if __name__ == '__main__':
    BasicCharacterizationParadigm().configure_traits()

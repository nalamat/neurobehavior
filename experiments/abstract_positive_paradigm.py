from enthought.traits.api import CBool
from enthought.traits.ui.api import View, VGroup, Include

from .abstract_experiment_paradigm import AbstractExperimentParadigm
from .evaluate import Expression

class AbstractPositiveParadigm(AbstractExperimentParadigm):
    
    kw = {'context': True, 'store': 'attribute', 'log': True}

    pump_rate = Expression(1.5, label='Pump rate (ml/min)', **kw)
    reward_volume = Expression(25, label='Reward volume (ul)', **kw)

    # Needs to be CBool because Pytables returns numpy.bool_ type which gets
    # rejected by Bool trait
    signal_offset_delay = Expression(0.5, label='Signal offset delay (s)', **kw)
    intertrial_duration = Expression(0.1, label='Intertrial duration (s)', **kw)
    reaction_window_delay = Expression(0, label='Withdraw delay (s)', **kw)
    reaction_window_duration = Expression(1.5, label='Withdraw duration (s)', **kw)
    response_window_duration = Expression(3, label='Response duration (s)', **kw)
    timeout_duration = Expression(1, label='TO duration (s)', **kw)
    fa_puff_duration = Expression(0.0, label='FA puff duration (s)', **kw)
    poke_duration = Expression(0.2, label='Poke duration (s)', **kw)

    abstract_positive_paradigm_group = VGroup(
            'signal_offset_delay',
            'intertrial_duration',
            'reaction_window_delay',
            'reaction_window_duration',
            'response_window_duration',
            'timeout_duration',
            'fa_puff_duration',
            'poke_duration',
            'pump_rate',
            'reward_volume',
            label='Paradigm',
            )

    traits_view = View(
            Include('abstract_positive_paradigm_group'),
            resizable=True,
            title='Abstract positive paradigm editor',
            width=100,
            )

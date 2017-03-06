from traits.api import Float, Bool
from traitsui.api import View, VGroup, Include

from .abstract_experiment_paradigm import AbstractExperimentParadigm
from .evaluate import Expression

class AbstractPositiveParadigm(AbstractExperimentParadigm):

    kw = {'context': True, 'log': True}
    kw2 = {'context': False, 'log': False}

    iti_duration      = Expression(0.1, label='Intertrial duration (s)', **kw)
    to_duration       = Expression(1  , label='TO duration (s)'        , **kw)
    hold_duration     = Expression(0.2, label='Hold duration (s)'      , **kw)
    response_duration = Expression(3  , label='Response duration (s)'  , **kw)
    np_duration       = Expression(0.2, label='Poke duration (s)'      , **kw)
    masker_frequency  = Expression(10 , label='Masker frequency (Hz)'  , **kw)
    phase_delay       = Expression(45 , label='Phase delay (deg)'      , **kw)
    pump_rate         = Expression(1.5, label='Pump rate (ml/min)'     , **kw)
    reward_volume     = Expression(25 , label='Reward volume (ul)'     , **kw)
    target_duration   = Expression(1  , label='Target duration (s)'      , **kw)
    # update_delay      = Expression(200, label='Update delay (ms)'      , **kw)

    abstract_positive_paradigm_group = VGroup(
            'iti_duration',
            'hold_duration',
            'response_duration',
            'to_duration',
            'np_duration',
            'masker_frequency',
            'phase_delay',
            'pump_rate',
            'reward_volume',
            'target_duration',
            # 'update_delay',
            label='Paradigm',
            show_border=True,
            )

    traits_view = View(
            Include('abstract_positive_paradigm_group'),
            resizable=True,
            title='Abstract positive paradigm editor',
            width=100,
            )

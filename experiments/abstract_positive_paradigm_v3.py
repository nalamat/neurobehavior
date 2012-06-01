from traits.api import Float
from traitsui.api import View, VGroup, Include

from .abstract_experiment_paradigm import AbstractExperimentParadigm
from .evaluate import Expression

class AbstractPositiveParadigm(AbstractExperimentParadigm):
    
    kw = {'context': True, 'log': True}

    speaker = Expression("random_speaker(0.5)", label='Output Speaker', **kw)

    pump_rate = Expression(1.5, label='Pump rate (ml/min)', **kw)
    reward_volume = Expression(25, label='Reward volume (ul)', **kw)
    signal_offset_delay = Expression(0.5, label='Signal offset delay (s)', **kw)
    intertrial_duration = Expression(0.1, label='Intertrial duration (s)', **kw)
    response_window_delay = Expression(0, label='Response delay (s)', **kw)
    response_window_duration = Expression(3, label='Response duration (s)', **kw)
    timeout_duration = Expression(1, label='TO duration (s)', **kw)
    poke_duration = Expression(0.2, label='Poke duration (s)', **kw)

    mic_fhp = Float(100, label='Microphone highpass cutoff (Hz)', **kw)
    mic_flp = Float(40e3, label='Microphone lowpass cutoff (Hz)', **kw)

    abstract_positive_paradigm_group = VGroup(
            'speaker',
            'signal_offset_delay',
            'intertrial_duration',
            'response_window_delay',
            'response_window_duration',
            'timeout_duration',
            'poke_duration',
            'pump_rate',
            'reward_volume',
            'mic_fhp',
            'mic_flp',
            label='Paradigm',
            show_border=True,
            )

    traits_view = View(
            Include('abstract_positive_paradigm_group'),
            resizable=True,
            title='Abstract positive paradigm editor',
            width=100,
            )

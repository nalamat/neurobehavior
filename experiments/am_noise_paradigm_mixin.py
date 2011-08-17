from enthought.traits.api import HasTraits
from enthought.traits.ui.api import VGroup
from evaluate import Expression

class AMNoiseParadigmMixin(HasTraits):
    
    kw = {'context': True, 'store': 'attribute', 'log': True}

    duration = Expression(1.2, label='Signal duration (s)', **kw)
    rise_fall_time = Expression(0.15, label='Ramp time (s)', **kw)
    fm = Expression(5, label='Modulation frequency (Hz)', **kw)
    level = Expression(60.0, label='Spectrum Level (dB SPL)', **kw)
    seed = Expression(-1, label='Noise seed', **kw)
    modulation_onset = Expression('uniform(0.1, 0.3)', 
                                  label='Modulation onset (s)', **kw)
    modulation_depth = Expression(1.0, label='Modulation depth (frac)', **kw)
    reaction_window_delay = Expression("modulation_onset+0.25",
                                       label='Reaction window delay (s)', **kw)

    am_noise_group = VGroup(
            'level',
            'duration',
            'rise_fall_time',
            'fm',
            'modulation_depth',
            'modulation_onset',
            'seed',
            label='Signal',
            show_border=True,
            )

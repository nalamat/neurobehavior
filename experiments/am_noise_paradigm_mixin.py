from enthought.traits.api import HasTraits
from enthought.traits.ui.api import VGroup
from evaluate import Expression

class AMNoiseParadigmMixin(HasTraits):
    
    kw = {'context': True, 'store': 'attribute', 'log': True}
    fc = Expression(3e3, label='Center frequency (Hz)', **kw)
    modulation_onset = Expression('uniform(0.2, 0.4)', label='Modulation onset (s)')
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
    bandwidth = Expression(3e3, label='Bandwidth (Hz)', **kw)
    rs = Expression(60, label='Minimum attenuation in stop band (dB)', **kw)
    rp = Expression(4, label='Maximum ripple in pass band (dB)', **kw)
    order = Expression(1, label='Filter order', **kw)

    # This defines what is visible via the GUI
    am_noise_group = VGroup(
            'duration',
            'rise_fall_time',
            'fm',
            'fc',
            'modulation_depth',
            'modulation_onset',
            'level',
            VGroup(
                'seed',
                'bandwidth',
                'rp',
                'rs',
                'order',
                label='Noise-specific settings',
                show_border=True,
                ),
            label='Signal',
            show_border=True,
            )

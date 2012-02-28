from traits.api import HasTraits
from traitsui.api import VGroup
from experiments.eval import Expression

class PositiveAMNoiseParadigmMixin(HasTraits):
    kw = {'context': True, 'store': 'attribute', 'log': True}

    # SAM envelope properties
    modulation_onset = Expression('0.3', label='Modulation onset (s)', **kw)
    fm = Expression(5, label='Modulation frequency (Hz)', **kw)
    modulation_depth = Expression(1.0, label='Modulation depth (frac)', **kw)
    modulation_direction = Expression("'positive'", 
            label='Initial modulation direction', **kw)

    # COS envelope properties
    duration = Expression(1.3, label='Signal duration (s)', **kw)
    rise_fall_time = Expression(0.25, label='Ramp time (s)', **kw)

    # Noise properties
    seed = Expression(-1, label='Noise seed', **kw)
    fc = Expression(3e3, label='Center frequency (Hz)', **kw)
    bandwidth = Expression(3e3, label='Bandwidth (Hz)', **kw)
    rs = Expression(60, label='Minimum attenuation in stop band (dB)', **kw)
    rp = Expression(4, label='Maximum ripple in pass band (dB)', **kw)
    order = Expression(1, label='Filter order', **kw)

    level = Expression(55.0, label='Spectrum Level (dB SPL)', **kw)

    # This defines what is visible via the GUI
    signal_group = VGroup(
            VGroup(
                'duration',
                'rise_fall_time',
                'fm',
                'fc',
                'modulation_depth',
                'modulation_onset',
                'level',
                'modulation_direction',
                label='Token settings',
                show_border=True,
                ),
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

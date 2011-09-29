from enthought.traits.api import HasTraits
from enthought.traits.ui.api import VGroup
from evaluate import Expression

class AMBBNParadigmMixin(HasTraits):
    
    kw = {'context': True, 'store': 'attribute', 'log': True}

    modulation_onset = Expression('uniform(0.2, 0.4)', label='Modulation onset (s)')
    fm = Expression(5, label='Modulation frequency (Hz)', **kw)
    level = Expression(60.0, label='Spectrum Level (dB SPL)', **kw)
    seed = Expression(-1, label='Noise seed', **kw)
    modulation_depth = Expression(1.0, label='Modulation depth (frac)', **kw)
    modulation_direction = Expression("'positive'", 
            label='Initial modulation direction', **kw)

    # This defines what is visible via the GUI
    signal_group = VGroup(
            'modulation_depth',
            'modulation_onset',
            'level',
            'modulation_direction',
            'seed',
            label='Signal',
            show_border=True,
            )

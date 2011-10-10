from enthought.traits.api import HasTraits
from enthought.traits.ui.api import VGroup
from evaluate import Expression

class FMParadigmMixin(HasTraits):
    '''
    Paradigm designed exclusively for FM tones.  Be sure to use with the
    appropriate DSP circuit.
    '''
    
    kw = {'context': True, 'store': 'attribute', 'log': True}

    depth = Expression(200, label='Modulation depth (Hz)', **kw)
    fc = Expression(4000, label='Carrier frequency (Hz)', **kw)
    fm = Expression(5, label='Modulation frequency (Hz)', **kw)
    level = Expression(0.0, label='Level (dB SPL)', **kw)

    signal_group = VGroup(
            'fc',
            'fm',
            'depth',
            'level',
            show_border=True, 
            label='FM parameters')

from enthought.traits.api import HasTraits
from enthought.traits.ui.api import VGroup
from evaluate import Expression

class FMAMParadigmMixin(HasTraits):
    '''
    Paradigm designed exclusively for AM and/or FM tones.  Be sure to use with
    the appropriate DSP circuit.
    '''
    
    kw = {'context': True, 'store': 'attribute', 'log': True}

    fc = Expression(4000, label='Carrier frequency (Hz)', **kw)
    level = Expression(0.0, label='Level (dB SPL)', **kw)
    fm_depth = Expression(200, label='FM depth (Hz)', **kw)
    fm_freq = Expression(5, label='FM frequency (Hz)', **kw)
    fm_direction = Expression("'positive'", **kw)
    am_depth = Expression(0, label='AM depth (Hz)', **kw)
    am_freq = Expression('fm_freq', label='AM frequency (Hz)', **kw)
    am_direction = Expression("'positive'", **kw)

    signal_group = VGroup(
            'fc',
            'level',
            'fm_depth',
            'fm_freq',
            'fm_direction',
            'am_depth',
            'am_freq',
            'am_direction',
            show_border=True, 
            label='FM/AM parameters')

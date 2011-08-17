from enthought.traits.api import Float, Range
from enthought.traits.ui.api import VGroup, Item

from abstract_aversive_paradigm import AbstractAversiveParadigm

from evaluate import Expression

class AversiveFMParadigm(AbstractAversiveParadigm):
    '''Aversive paradigm designed exclusively for FM tones.  Be sure to use with
    the appropriate DSP circuit.
    '''
    
    kw = {'context': True, 'store': 'attribute'}

    depth = Expression(200, label='Modulation depth (Hz)', **kw)
    cf = Expression(4000, label='Carrier frequency (Hz)', **kw)
    fm = Expression(5, label='Modulation frequency (Hz)', **kw)
    attenuation = Expression(0.0, label='Attenuation (dB)', **kw)

    signal_group = VGroup(
            'cf',
            'fm',
            'depth',
            'attenuation',
            show_border=True, 
            label='FM parameters')

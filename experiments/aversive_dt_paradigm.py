from enthought.traits.api import Float, Range
from enthought.traits.ui.api import VGroup, Item

from abstract_aversive_paradigm import AbstractAversiveParadigm

from evaluate import Expression

class AversiveDTParadigm(AbstractAversiveParadigm):
    '''Aversive paradigm designed exclusively for FM tones.  Be sure to use with
    the appropriate DSP circuit.
    '''
    kw = {'context': True, 'store': 'attribute'}
    
    ramp_duration = Expression(0.0025, label='Ramp duration (s)', **kw)
    frequency = Expression(4000, label='Frequency (Hz)', **kw)
    attenuation = Expression(0.0, label='Attenuation (dB)', **kw)

    signal_group = VGroup(
            'frequency',
            'attenuation',
            show_border=True, 
            label='Tone parameters')

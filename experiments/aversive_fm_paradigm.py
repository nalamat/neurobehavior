from enthought.traits.api import Float, Range
from enthought.traits.ui.api import VGroup, Item

from abstract_aversive_paradigm import AbstractAversiveParadigm

from eval import ExpressionTrait

class AversiveFMParadigm(AbstractAversiveParadigm):
    '''Aversive paradigm designed exclusively for FM tones.  Be sure to use with
    the appropriate DSP circuit.
    '''

    depth = ExpressionTrait(200, label='Modulation depth (Hz)')
    cf = ExpressionTrait(4000, label='Carrier frequency (Hz)')
    fm = ExpressionTrait(5, label='Modulation frequency (Hz)')
    attenuation = ExpressionTrait(0.0, label='Attenuation (dB)')

    signal_group = VGroup(
            'cf',
            'fm',
            'depth',
            'attenuation',
            show_border=True, 
            label='FM parameters')

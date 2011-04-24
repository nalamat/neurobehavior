from enthought.traits.api import Float, Range
from enthought.traits.ui.api import VGroup, Item

from abstract_aversive_paradigm import AbstractAversiveParadigm

from eval import ExpressionTrait

class AversiveDTParadigm(AbstractAversiveParadigm):
    '''Aversive paradigm designed exclusively for FM tones.  Be sure to use with
    the appropriate DSP circuit.
    '''

    ramp_duration = ExpressionTrait(0.0025, label='Ramp duration (s)')
    frequency = ExpressionTrait(4000, label='Frequency (Hz)')
    attenuation = ExpressionTrait(0.0, label='Attenuation (dB)')

    signal_group = VGroup(
            'frequency',
            'attenuation',
            show_border=True, 
            label='Tone parameters')

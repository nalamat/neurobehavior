from enthought.traits.api import Float, Range
from enthought.traits.ui.api import VGroup, Item

from abstract_aversive_paradigm import AbstractAversiveParadigm

class AversiveFMParadigm(AbstractAversiveParadigm):
    '''Aversive paradigm designed exclusively for FM tones.  Be sure to use with
    the appropriate DSP circuit.
    '''

    carrier_frequency = Float(4000, store='attribute')
    modulation_frequency = Float(5, store='attribute')
    attenuation = Range(0, 120, 40, store='attribute')

    signal_group = VGroup(
            Item('carrier_frequency', label='Carrier frequency (Hz)'),
            Item('modulation_frequency', label='Modulation frequency (Hz)'),
            Item('attenuation', label='Attenuation (dB)'),
            show_border=True, label='FM parameters')


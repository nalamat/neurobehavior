from enthought.traits.api import Float, Range
from enthought.traits.ui.api import Item, VGroup
from abstract_aversive_paradigm import AbstractAversiveParadigm

class AversiveAMNoiseParadigm(AbstractAversiveParadigm):
    '''Generic aversive paradigm designed to work with most classes of signals.
    Note that this will not work well with modulated tones!
    '''

    modulation_frequency = Float(5, store='attribute')
    attenuation = Range(0.0, 120.0, 20, store='attribute')

    signal_group = VGroup(
            Item('attenuation', label='Attenuation (dB)', style='text'),
            Item('modulation_frequency', label='Modulation frequency (Hz)'),
            show_border=True, label='Signal',
            )

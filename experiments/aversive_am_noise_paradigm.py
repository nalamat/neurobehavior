from enthought.traits.api import Float, Range
from enthought.traits.ui.api import Item, VGroup
from abstract_aversive_paradigm import AbstractAversiveParadigm

class AversiveAMNoiseParadigm(AbstractAversiveParadigm):
    '''Generic aversive paradigm designed to work with most classes of signals.
    Note that this will not work well with modulated tones!
    '''

    modulation_depth = Float(1, store='attribute', init=True)
    modulation_frequency = Float(5, store='attribute')
    attenuation = Range(0.0, 120.0, 20, store='attribute', init=True)

    signal_group = VGroup(
            Item('attenuation', label='Attenuation (dB)', style='text'),
            Item('modulation_frequency', label='Modulation frequency (Hz)'),
            Item('modulation_depth', label='Modulation depth (fraction)'),
            show_border=True, label='Signal',
            )

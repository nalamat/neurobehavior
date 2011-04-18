from enthought.traits.api import Float, Range
from enthought.traits.ui.api import VGroup, Item

from abstract_aversive_paradigm import AbstractAversiveParadigm

from eval import ExpressionTrait

class AversiveFMParadigm(AbstractAversiveParadigm):
    '''Aversive paradigm designed exclusively for FM tones.  Be sure to use with
    the appropriate DSP circuit.
    '''

    def get_parameters(self):
        filter = {
                'editable': lambda x: x is not False,
                'type':     lambda x: x != 'event',
                'ignore':   lambda x: x is not True,
                }
        return sorted(self.trait_names(**filter))

    modulation_depth        = ExpressionTrait(200)
    carrier_frequency       = ExpressionTrait(4000)
    modulation_frequency    = ExpressionTrait(5)
    attenuation             = ExpressionTrait(0.0)

    signal_group = VGroup(
            Item('carrier_frequency', label='Carrier frequency (Hz)'),
            Item('modulation_frequency', label='Modulation frequency (Hz)'),
            Item('modulation_depth', label='Modulation depth (Hz)'),
            Item('attenuation', label='Attenuation (dB)', style='text'),
            show_border=True, label='FM parameters')

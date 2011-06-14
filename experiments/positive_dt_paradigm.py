from enthought.traits.api import Float, Range, List, Instance, HasTraits, Enum
from enthought.traits.ui.api import *

from abstract_positive_paradigm import AbstractPositiveParadigm
from eval import ExpressionTrait

class PositiveDTParadigm(AbstractPositiveParadigm):

    rise_fall_time      = ExpressionTrait(0.0025, label='Rise/fall time (s)')
    fc                  = ExpressionTrait(12e3, label='Center frequency (Hz)')
    bandwidth           = ExpressionTrait(4e3, label='Bandwidth (Hz)')
    attenuation         = ExpressionTrait(20, label='Attenuation (dB)')
    primary_attenuation = Enum(60, 0, 20, 40, 60, store='attribute', init=True,
                                label='Primary attenuation (dB)')
    secondary_attenuation = Enum(60, 0, 20, 40, 60, store='attribute', init=True,
                                label='Secondary attenuation (dB)')
    duration            = ExpressionTrait(0.512, label='Duration (s)')

    signal_group = VGroup(
            'speaker_mode',
            'duration',
            'rise_fall_time',
            'fc',
            'bandwidth',
            'primary_attenuation',
            'secondary_attenuation',
            label='Signal'
            )

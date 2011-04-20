from enthought.traits.api import Float, Range, List, Instance, HasTraits, Enum
from enthought.traits.ui.api import *

from abstract_positive_paradigm import AbstractPositiveParadigm

class PositiveDTParadigm(AbstractPositiveParadigm):

    rise_fall_time      = Float(0.0025, store='attribute', init=True,
                                label='Rise/fall time (s)')
    fc                  = Float(12e3, store='attribute', init=True,
                                label='Center frequency (Hz)')
    bandwidth           = Float(4e3, store='attribute', init=True,
                                label='Bandwidth (Hz)')
    attenuation         = Float(20, store='attribute', init=True,
                                label='Attenuation (dB)')
    primary_attenuation = Enum(60, 0, 20, 40, 60, store='attribute', init=True,
                                label='Primary attenuation (dB)')
    secondary_attenuation = Enum(60, 0, 20, 40, 60, store='attribute', init=True,
                                label='Secondary attenuation (dB)')
    duration            = Float(0.512, store='attribute', init=True,
                                label='Duration (s)')

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

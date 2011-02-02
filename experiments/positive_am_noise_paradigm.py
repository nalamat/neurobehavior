from enthought.traits.api import Float, Range
from enthought.traits.ui.api import VGroup, Item

from abstract_positive_paradigm import AbstractPositiveParadigm

class PositiveAMNoiseParadigm(AbstractPositiveParadigm):

    duration = Float(1, store='attribute')
    rise_fall_time = Float(0.0025, store='attribute')
    fm = Float(5, store='attribute')
    attenuation = Range(0.0, 120.0, 30.0, store='attribute')

    signal_group = VGroup(
            Item('attenuation', label='Signal attenuation (dB)'),
            Item('duration', label='Signal duration (s)'),
            Item('rise_fall_time', label='Rise/fall time (s)'),
            Item('fm', label='Modulation frequency (Hz)'),
            label='AM noise settings',
            show_border=True,
            )

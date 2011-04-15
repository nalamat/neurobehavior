from enthought.traits.api import Float, Range, Int
from enthought.traits.ui.api import VGroup, Item

from abstract_positive_paradigm import AbstractPositiveParadigm

class PositiveAMNoiseParadigm(AbstractPositiveParadigm):

    duration = Float(1, store='attribute', init=True)
    rise_fall_time = Float(0.0025, store='attribute', init=True)
    fm = Float(5, store='attribute', init=True)
    attenuation = Range(0.0, 120.0, 30.0, store='attribute', init=True)
    seed = Int(-1, store='attribute', init=True)
    lb_modulation_onset = Float(0.5, store='attribute', init=True)
    ub_modulation_onset = Float(1.0, store='attribute', init=True)

    signal_group = VGroup(
            Item('speaker_mode', label='Speaker'),
            Item('attenuation', style='custom', 
                 label='Signal attenuation (dB)'),
            Item('duration', label='Signal duration (s)'),
            Item('rise_fall_time', label='Rise/fall time (s)'),
            Item('fm', label='Modulation frequency (Hz)'),
            Item('lb_modulation_onset', label='lb modulation onset (s)'),
            Item('ub_modulation_onset', label='ub modulation onset (s)'),
            Item('seed', label='Random seed (-1=nonfrozen)'),
            label='Signal',
            show_border=True,
            )

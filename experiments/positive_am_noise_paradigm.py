from enthought.traits.api import Float, Range, Int
from enthought.traits.ui.api import VGroup, Item

from eval import ExpressionTrait

from abstract_positive_paradigm import AbstractPositiveParadigm

class PositiveAMNoiseParadigm(AbstractPositiveParadigm):

    duration = ExpressionTrait(1, label='Signal duration (s)')
    rise_fall_time = ExpressionTrait(0.0025, label='Ramp time (s)')
    fm = ExpressionTrait(5, label='Modulation frequency (Hz)')
    attenuation = ExpressionTrait(30.0, label='Attenuation (dB)')
    seed = Int(-1, store='attribute', init=True)
    modulation_onset = ExpressionTrait('uniform(0.5, 1.0)', 
            label='Modulation onset (s)')
    modulation_depth = ExpressionTrait(1.0, label='Modulation depth (frac)')

    reaction_window_delay = ExpressionTrait("modulation_onset+0.25",
            label='Reaction window delay (s)')

    signal_group = VGroup(
            'speaker_mode',
            'attenuation',
            'duration',
            'rise_fall_time',
            'fm',
            'modulation_depth',
            'modulation_onset',
            'seed',
            label='Signal',
            show_border=True,
            )


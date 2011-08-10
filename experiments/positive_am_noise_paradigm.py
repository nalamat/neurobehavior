from enthought.traits.api import Float, Range, Int
from enthought.traits.ui.api import VGroup, Item

from eval import ExpressionTrait

from abstract_positive_paradigm import AbstractPositiveParadigm

class PositiveAMNoiseParadigm(AbstractPositiveParadigm):

    duration = ExpressionTrait(1, label='Signal duration (s)')
    rise_fall_time = ExpressionTrait(0.0025, label='Ramp time (s)')
    fm = ExpressionTrait(5, label='Modulation frequency (Hz)')
    fc = ExpressionTrait(3e3, label='Center frequency (Hz)')
    attenuation = ExpressionTrait(30.0, label='Attenuation (dB)')
    seed = Int(-1, store='attribute', init=True)
    modulation_onset = ExpressionTrait('uniform(0.5, 1.0)', label='Modulation onset (s)')
    modulation_depth = ExpressionTrait(1.0, label='Modulation depth (frac)')
    reaction_window_delay = ExpressionTrait("modulation_onset+0.25",
            label='Reaction window delay (s)')
    
    bandwidth = ExpressionTrait(3e3, label='Bandwidth (Hz)')
    rs = ExpressionTrait(60, label='Minimum attenuation in stop band (dB)')
    rp = ExpressionTrait(4, label='Maximum ripple in pass band (dB)')
    order = ExpressionTrait(1, label='Filter order')

    # This defines what is visible via the GUI
    signal_group = VGroup(
            'speaker_mode',
            'attenuation',
            'duration',
            'rise_fall_time',
            'fm',
            'fc',
            'modulation_depth',
            'modulation_onset',
            VGroup(
                'seed',
                'bandwidth',
                'rp',
                'rs',
                'order',
                label='Noise-specific settings',
                show_border=True,
                ),
            label='Signal',
            show_border=True,
            )


from enthought.traits.api import Int, Float
from enthought.traits.ui.api import VGroup, Item

from abstract_aversive_paradigm import AbstractAversiveParadigm

class AversiveNoiseMaskingParadigm(AbstractAversiveParadigm):

    # Define your variables here.  Be sure to set store value to attribute.
    # This tells my code to save the value of that attribute in the data file.
    repeats = Int(3, store='attribute')
    masker_duration = Float(0.5, store='attribute')
    masker_amplitude = Float(1, store='atribute')
    probe_duration = Float(0.1, store='attribute')
    trial_duration = Float(1, store='attribute')

    signal_group = VGroup(
            Item('repeats'),
            Item('masker_duration'),
            Item('masker_amplitude'),
            Item('probe_duration'),
            label='Masker Settings',
            show_border=True,
            )

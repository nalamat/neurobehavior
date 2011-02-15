from enthought.traits.api import Int, Float, Instance, List, HasTraits, \
        Float, Enum
from enthought.traits.ui.api import VGroup, Item, TableEditor, ObjectColumn, \
        View, HGroup

from abstract_aversive_paradigm import AbstractAversiveParadigm

class TrialShockSetting(HasTraits):

    parameter           = Float(store='attribute')
    shock_level         = Float(store='attribute')
    traits_view         = View('parameter', 'shock_level')

    def __str__(self):
        return "{0} with a shock level of {1}".format(self.parameter, self.shock_level)

    def __cmp__(self, other):
        # We want them to be sorted by the parameter, which is important for
        # controlling whether the sequence is ascending or descending.
        return cmp(self.parameter, other.parameter)

table_editor = TableEditor(
        reorderable=True,
        editable=True,
        deletable=True,
        show_toolbar=True,
        row_factory=TrialShockSetting,
        selection_mode='cell',
        columns=[
            ObjectColumn(name='parameter', label='Tone dB level', width=75),
            ObjectColumn(name='shock_level', label='Shock level', width=75),
            ]
        )


class AversiveNoiseMaskingParadigm(AbstractAversiveParadigm):

    # The AbstractAversiveParadigm uses a "default" parameter sequence.  We want
    # to include a shock setting, so we override that default.
    warn_sequence = List(Instance(TrialShockSetting), minlen=1,
                         editor=table_editor, store='child')
    remind        = Instance(TrialShockSetting, (), store='child')
    safe          = Instance(TrialShockSetting, (), store='child')

    def _warn_sequence_default(self):
        return [TrialShockSetting()]

    # Define your variables here.  Be sure to set store value to attribute.
    # This tells my code to save the value of that attribute in the data file.
    repeats = Int(3, store='attribute')
    masker_duration = Float(0.2, store='attribute')
    masker_amplitude = Float(0.5, store='atribute')
    probe_duration = Float(0.01, store='attribute')
    trial_duration = Float(0.5, store='attribute')

    signal_group = VGroup(
            Item('repeats'),
            Item('masker_duration'),
            Item('masker_amplitude'),
            Item('probe_duration'),
            label='Masker Settings',
            show_border=True,
            )

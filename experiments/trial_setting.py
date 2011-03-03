from enthought.traits.api import HasTraits, Float, Enum
from enthought.traits.ui.api import TableEditor, ObjectColumn, View, HGroup

class TrialSetting(HasTraits):

    parameter           = Float(store='attribute')

    traits_view         = View(HGroup('parameter'))

    def __str__(self):
        return "{0}".format(self.parameter)

    def __cmp__(self, other):
        # We want them to be sorted by the parameter, which is important for
        # controlling whether the sequence is ascending or descending.
        return cmp(self.parameter, other.parameter)

trial_setting_editor = TableEditor(
        reorderable=True,
        editable=True,
        deletable=True,
        show_toolbar=True,
        row_factory=TrialSetting,
        selection_mode='cell',
        columns=[
            ObjectColumn(name='parameter', label='Parameter', width=75),
            ]
        )

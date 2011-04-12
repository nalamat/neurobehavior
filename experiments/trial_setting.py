from enthought.traits.api import HasTraits, Float, Enum
from enthought.traits.ui.api import TableEditor, ObjectColumn, View, HGroup

class TrialSetting(HasTraits):

    def traits_view(self):
        return View(HGroup(*self.parameters))

    def parameter_dict(self):
        return dict(zip(self.parameters, self.parameter_values()))

    def parameter_values(self):
        return [getattr(self, p) for p in self.parameters]

    def __str__(self):
        pars = zip(self.parameters, self.parameter_values())
        return ', '.join('{}: {}'.format(n, v) for n, v in pars)

    def __cmp__(self, other):
        # We want them to be sorted by the parameter, which is important for
        # controlling whether the sequence is ascending or descending.
        return cmp(self.parameter_values(), other.parameter_values())

trial_setting_editor = TableEditor(
        reorderable=True,
        editable=True,
        deletable=True,
        show_toolbar=True,
        row_factory=TrialSetting,
        selection_mode='cell',
        columns=[],
        )

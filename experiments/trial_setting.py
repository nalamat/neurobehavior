from enthought.traits.api import HasTraits, Float
from enthought.traits.ui.api import TableEditor, ObjectColumn, View, HGroup

class TrialShockSetting(HasTraits):

    parameter = Float
    shock_level = Float

    traits_view = View(HGroup('parameter', 'shock_level'))


# This will be auto-generated soon
table_editor = TableEditor(
        editable=True,
        deletable=True,
        show_toolbar=True,
        row_factory=TrialShockSetting,
        columns=[
            ObjectColumn(name='parameter', label='Parameter', width=75),
            ObjectColumn(name='shock_level', label='Reward rate', width=75),
            ]
        )

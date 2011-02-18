from enthought.traits.api import HasTraits, Float, Enum
from enthought.traits.ui.api import TableEditor, ObjectColumn, View, HGroup

class TrialShockSetting(HasTraits):

    parameter           = Float(store='attribute')
    aversive_duration   = Float(store='attribute')
    traits_view         = View(HGroup('parameter', 'shock_level'))
#    traits_view         = View('parameter')

    def __str__(self):
        return "{0}".format(self.parameter)

    def __cmp__(self, other):
        # We want them to be sorted by the parameter, which is important for
        # controlling whether the sequence is ascending or descending.
        return cmp(self.parameter, other.parameter)

#class SettingColumn(ObjectColumn):
#
#    COLORS = {
#            'warn'  : 'lightpink',
#            'safe'  : 'lightgreen', #            'remind': 'lightgray',
#            }
#
#    def get_cell_color(self, object):
#        return self.COLORS[object.trial_type]

# This will be auto-generated soon

table_editor = TableEditor(
        reorderable=True,
        editable=True,
        deletable=True,
        show_toolbar=True,
        row_factory=TrialShockSetting,
        selection_mode='cell',
        columns=[
            #SettingColumn(name='trial_type', label='Type', width=75),
            ObjectColumn(name='parameter', label='Parameter', width=75),
            ObjectColumn(name='shock_level', label='Shock level', width=75),
            #ObjectColumn(name='aversive_duration', label='Aversive duration (s)', width=75),
            ]
        )

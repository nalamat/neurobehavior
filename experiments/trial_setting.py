from enthought.traits.api import HasTraits, Enum, TraitError, Float, Int,\
     List, Str
from enthought.traits.ui.api import TableEditor, View, HGroup

class TrialSetting(HasTraits):
    
    parameters = []
    
    def __init__(self, *parameters, **kwargs):
        for value, name in zip(parameters, self.parameters):
            kwargs[name] = value
        super(TrialSetting, self).__init__(**kwargs)

    def traits_view(self):
        return View(HGroup(*self.parameters))

    def parameter_dict(self):
        return dict(zip(self.parameters, self.parameter_values()))

    def parameter_values(self):
        return [getattr(self, p) for p in self.parameters]

    def __str__(self):
        pars = zip(self.parameters, self.parameter_values())
        return ', '.join('{}: {}'.format(n, v) for n, v in pars)

    def __repr__(self):
        return '<TrialSetting {}>'.format(str(self))

    def __cmp__(self, other):
        # We want them to be sorted by the parameters, which is important for
        # controlling whether the sequence is ascending or descending. If roving
        # by multiple parameters, then the order the parameters are specified in
        # the list will determine the sort order priority.
        try:
            return cmp(self.parameter_values(), other.parameter_values())
        except AttributeError:
            return -1

from enthought.traits.ui.api import TabularEditor
from enthought.traits.ui.tabular_adapter import TabularAdapter

trial_setting_editor = TabularEditor(
    auto_update=True,
    editable=True, 
    multi_select=True,
    selected='_selected_setting',
    adapter=TabularAdapter(width=100)
)

def add_parameters(parameters, paradigm_class=None, repeats=True):
    '''
    Modifies the TrialSetting class on-the fly to control the parameters we want
    '''
    columns = []
    for parameter in parameters:
        # Get the human-readable label from the class definition if it is
        # available, otherwise set the label to the computer-representation of
        # the parameter name.
        if paradigm_class is not None:
            label = paradigm_class.class_traits()[parameter].label
        else:
            label = parameter

        trait = Float(label=label, store='attribute', context=True, log=False)
        TrialSetting.add_class_trait(parameter, trait)
        column = ((label, parameter))
        columns.append(column)

    if repeats:
        # Repeats is a special variable that tells us how many times a single
        # TrialSetting object should be presented during a sequence
        trait = Int(1, label='Repeats', store='attribute', context=True,
                    log=False)
        TrialSetting.add_class_trait('repeats', trait)
        column = (('Repeats', 'repeats'))
        columns.append(column)
    TrialSetting.parameters = parameters
    trial_setting_editor.adapter.columns = columns

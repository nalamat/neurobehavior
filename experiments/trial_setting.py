from enthought.traits.api import HasTraits, Enum, TraitError, Float, Int,\
     List, Str
from enthought.traits.ui.api import TableEditor, View, VGroup

class TrialSetting(HasTraits):
    
    _parameters = []
    _labels = []
    
    def __init__(self, *parameters, **kwargs):
        for value, name in zip(parameters, self._parameters):
            kwargs[name] = value
        super(TrialSetting, self).__init__(**kwargs)
        
    # How should the object appear under various contexts (GUI, command line, etc)

    def traits_view(self):
        return View(VGroup(*self._parameters))

    def __str__(self):
        lv = zip(self._labels, self.values())
        return ', '.join('{}: {}'.format(l, v) for l, v in lv)

    def __repr__(self):
        string = ', '.join('{}={}'.format(k, v) for k, v in self.items())
        return '<TrialSetting::{}>'.format(string)

    # Implement rich comparision operator for sorting and comparision as needed

    def __lt__(self, other):
        if not isinstance(other, TrialSetting):
            return NotImplemented
        return self.values() < other.values()

    def __ge__(self, other):
        if not isinstance(other, TrialSetting):
            return NotImplemented
        return self.values() > other.values()

    def __eq__(self, other):
        if not isinstance(other, TrialSetting):
            return NotImplemented
        return self.values() == other.values()

    def __ne__(self, other):
        if not isinstance(other, TrialSetting):
            return NotImplemented
        return self.values() != other.values()

    # Create a dictionary interface to facilitate setting the context values

    def values(self):
        return [getattr(self, p) for p in self._parameters]

    def keys(self):
        return self._parameters

    def items(self):
        return zip(self.keys(), self.values())

    def iteritems(self):
        return iter(self.items())

    def __getitem__(self, key):
        if key not in self._parameters:
            raise KeyError, key
        return getattr(self, key)

    def __len__(self):
        return len(self._parameters)

    def __iter__(self):
        return iter(self._parameters)

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
    labels = []
    for parameter in parameters:
        # Get the human-readable label from the class definition if it is
        # available, otherwise set the label to the computer-representation of
        # the parameter name.
        if paradigm_class is not None:
            label = paradigm_class.class_traits()[parameter].label
        else:
            label = parameter

        trait = Float(label=label, context=True, store='attribute', log=False)
        TrialSetting.add_class_trait(parameter, trait)
        column = ((label, parameter))
        columns.append(column)
        labels.append(label)

    if repeats:
        # Repeats is a special variable that tells us how many times a single
        # TrialSetting object should be presented during a sequence
        trait = Int(1, label='Repeats', store='attribute', context=True, log=False)
        column = (('Repeats', 'repeats'))
        columns.append(column)
        TrialSetting.add_class_trait('repeats', trait)

    trial_setting_editor.adapter.columns.extend(columns)
    TrialSetting._parameters.extend(parameters)
    TrialSetting._labels.extend(labels)

if __name__ == '__main__':
    add_parameters(['x', 'y'])
    s = TrialSetting()

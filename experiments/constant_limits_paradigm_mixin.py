from enthought.traits.api import (HasTraits, Instance, Button, List, Trait,
        Bool, Property)
from enthought.traits.ui.api import View, VGroup, HGroup, Item, Include
from copy import copy

from cns import choice

from .trial_setting import TrialSetting, trial_setting_editor
from .evaluate import Expression

class ConstantLimitsParadigmMixin(HasTraits):

    editable_nogo = Bool(True)

    kw = { 'log': False, 'container': True, 'context': True, 'store': 'child' }

    trial_settings = List(Instance(TrialSetting), store='child')
    remind_setting = Property(Instance(TrialSetting),
            depends_on='trial_settings', **kw)
    nogo_setting = Property(Instance(TrialSetting), 
            depends_on='trial_settings', **kw)
    go_settings = Property(List(Instance(TrialSetting)),
            depends_on='trial_settings', **kw)

    kw = { 'log': True, 'context': True, 'store': 'attribute' }

    go_setting_order = Trait('shuffled set', choice.options, 
            label='Go setting order', **kw)
    go_probability = Expression('0.5 if c_nogo < 5 else 1', 
            label='Go probability', **kw)
    repeat_fa = Bool(True, label='Repeat nogo if FA?', **kw)

    # GUI elements to facilitate adding and removing parameters from the go
    # settings list.
    _add = Button()
    _remove = Button()
    _sort = Button()
    _selected_setting = List(Instance(TrialSetting), transient=True)

    def _get_nogo_setting(self):
        if self.editable_nogo:
            return self.trial_settings[0]
        else:
            return TrialSetting('NOGO')

    def _get_remind_setting(self):
        if self.editable_nogo:
            return self.trial_settings[1]
        else:
            return self.trial_settings[0]

    def _get_go_settings(self):
        if self.editable_nogo:
            return self.trial_settings[2:]
        else:
            return self.trial_settings[1:]

    def _trial_settings_default(self):
        if self.editable_nogo:
            return [TrialSetting('NOGO'), 
                    TrialSetting('GO_REMIND'),
                    TrialSetting('GO')]
        else:
            return [TrialSetting('GO_REMIND'),
                    TrialSetting('GO')]

    def __sort_fired(self):
        new_list = self.trial_settings[:2]
        go_trials = self.trial_settings[2:]
        go_trials.sort()
        new_list.extend(go_trials)
        self.trial_settings = new_list
    
    def __add_fired(self):
        # If a setting is selected, let's assume that the user wishes to
        # duplicate 
        if len(self._selected_setting) != 0:
            for setting in self._selected_setting:
                new = setting.clone_traits()
                new.ttype = 'GO'
                self.trial_settings.append(new)
        else:
            self.trial_settings.append(TrialSetting('GO'))
        
    def __remove_fired(self):
        for setting in self._selected_setting:
            if setting not in self.trial_settings[:2]:
                self.trial_settings.remove(setting)
        self._selected_setting = []

    cl_trial_setting_group = VGroup(
            HGroup('_add', '_remove', '_sort', show_labels=False),
            Item('trial_settings', editor=trial_setting_editor,
                 show_label=False))

    constant_limits_paradigm_mixin_group = VGroup(
        VGroup(
            Item('go_probability'),
            Item('go_setting_order'),
            Item('repeat_fa')
            ),
        Include('cl_trial_setting_group'),
        label='Constant limits',
        show_border=True,
        )
    
    traits_view = View(constant_limits_paradigm_mixin_group)

if __name__ == '__main__':
    from trial_setting import add_parameters
    add_parameters(['test'])
    ConstantLimitsParadigmMixin().configure_traits()

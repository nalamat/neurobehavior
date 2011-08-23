from enthought.traits.api import HasTraits, Instance, Button, List, Trait, Bool
from enthought.traits.ui.api import View, VGroup, HGroup, Item
from copy import copy

from cns import choice

from .trial_setting import TrialSetting, trial_setting_editor
from .evaluate import Expression

class ConstantLimitsParadigmMixin(HasTraits):

    remind_setting = Instance(TrialSetting, (), log=False, container=True,
            context=True, label='Remind setting')
    nogo_setting = Instance(TrialSetting, (), log=False, container=True,
            context=True, label='Nogo setting')

    go_settings = List(Instance(TrialSetting), container=True, context=True)
    go_setting_order = Trait('shuffled set', choice.options, context=True,
            label='Go setting order', log=True)
    go_probability = Expression('0.5 if c_nogo < 5 else 1', store='attribute',
            context=True, label='Go probability', log=True)
    repeat_fa = Bool(True, store='attribute', context=True, 
            label='Repeat nogo if FA?', log=True)

    # GUI elements to facilitate adding and removing parameters from the
    # go settings list.

    _add = Button()
    _remove = Button()
    _sort = Button()
    _selected_setting = List(Instance(TrialSetting), ignore=True)

    def _go_settings_default(self):
        return [TrialSetting()]

    def __sort_fired(self):
        self.go_settings.sort()
    
    def __add_fired(self):
        # If a setting is selected, let's assume that the user wishes to
        # duplicate 
        if len(self._selected_setting) != 0:
            for setting in self._selected_setting:
                new = TrialSetting()
                new.copy_traits(setting)
                self.go_settings.append(new)
        else:
            self.go_settings.append(TrialSetting())
        
    def __remove_fired(self):
        for setting in self._selected_setting:
            self.go_settings.remove(setting)

    constant_limits_paradigm_mixin_group = VGroup(
        VGroup(
            HGroup(
                Item('remind_setting', style='custom', show_label=False),
                label='Remind', show_border=True,
                ),
            HGroup(
                Item('nogo_setting', style='custom', show_label=False),
                label='Nogo', show_border=True,
                ),
            Item('go_probability'),
            Item('go_setting_order'),
            Item('repeat_fa')
            ),
        VGroup(
            HGroup('_add', '_remove', '_sort', show_labels=False),
            Item('go_settings', editor=trial_setting_editor,
                 show_label=False),                
            ),
        label='Constant limits',
        )
    
    traits_view = View(constant_limits_paradigm_mixin_group)

if __name__ == '__main__':
    from trial_setting import add_parameters
    add_parameters(['test'])
    ConstantLimitsParadigmMixin().configure_traits()

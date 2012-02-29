from enthought.traits.api import (HasTraits, Instance, Button, List, Trait,
        Bool, Property)
from enthought.traits.ui.api import View, VGroup, HGroup, Item, Include

from cns import choice

from .trial_setting import TrialSetting, trial_setting_editor
from .evaluate import Expression

# Right now the constant limits paradigm requires that there be one and only one
# GO_REMIND and one and only one NOGO.  However, there is no reason why one
# cannot have multiple reminds and/or nogos.  Until someone implements the
# error-checking and control logic for handling multiple reminds/nogos, I have
# put in several checks to ensure that the user cannot add an extra nogo or
# remind.  For example, whenever the trial_settings changes, I have a function
# that scans the list to remove duplicate reminds and nogos and add a nogo and
# remind back in if they are missing.  Also, in the add/remove events, I do not
# allow the user to add another nogo/remind or remove the existing nogo/remind.
# Likewise, I do not allow the user to remove the last GO from the list.

class CLParadigmMixin(HasTraits):

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

    def _trial_settings_changed(self, settings):
        nogo_found = False
        for ts in settings:
            if nogo_found and ts.ttype == 'NOGO':
                # This is a duplicate nogo.  We need to remove it.
                settings.remove(ts)
            elif not nogo_found and ts.ttype == 'NOGO':
                # We've found our nogo!
                nogo_found = True
        if not nogo_found:
            # The list is missing a nogo.  Let's add it.
            settings.append(TrialSetting('NOGO'))

        remind_found = False
        for ts in settings:
            if remind_found and ts.ttype == 'GO_REMIND':
                # This is a duplicate remind.  We need to remove it.
                settings.remove(ts)
            elif not remind_found and ts.ttype == 'GO_REMIND':
                # We've found our remind!
                remind_found = True
        if not remind_found:
            # The list is missing a remind.  Let's add it.
            settings.append(TrialSetting('GO_REMIND'))

        go_found = False
        for ts in settings:
            if not go_found and ts.ttype == 'GO':
                # We've found our remind!
                go_found = True
        if not go_found:
            # The list is missing a go.  Let's add it.
            settings.append(TrialSetting('GO'))

    def _get_nogo_setting(self):
        ts = [t for t in self.trial_settings if t.ttype == 'NOGO']
        if len(ts) > 1:
            raise ValueError, "Only one nogo can be specified!"
        elif len(ts) < 1:
            raise ValueError, "One nogo must be specified!"
        return ts[0]

    def _get_remind_setting(self):
        ts = [t for t in self.trial_settings if t.ttype == 'GO_REMIND']
        if len(ts) > 1:
            raise ValueError, "Only one remind can be specified!"
        elif len(ts) < 1:
            raise ValueError, "One remind must be specified!"
        return ts[0]

    def _get_go_settings(self):
        ts = [t for t in self.trial_settings if t.ttype == 'GO']
        if len(ts) < 1:
            raise ValueError, "At least one go must be specified"
        return ts

    def _trial_settings_default(self):
        return [TrialSetting('NOGO'), TrialSetting('GO_REMIND'),
                TrialSetting('GO')]

    def __sort_fired(self):
        self.trial_settings.sort()
    
    def __add_fired(self):
        # If some settings are selected, let's assume that the user wishes to
        # duplicate these
        if len(self._selected_setting) != 0:
            for setting in self._selected_setting:
                new = setting.clone_traits()
                new.ttype = 'GO'
                self.trial_settings.append(new)
        else:
            self.trial_settings.append(TrialSetting('GO'))
        
    def __remove_fired(self):
        for setting in self._selected_setting:
            # If the ttype is a NOGO or GO_REMIND, we do not remove these
            # because these are the only NOGO/GO_REMIND values in the list (this
            # is enforced by the __add_fired and _trial_settings_changed logic
            # in this class).  Likewise, if the length of trial_settings is 3,
            # this means that the user is trying to remove the only go that
            # remains in the list.  We must have at least one go, so we disallow
            # this attempt.
            if setting.ttype == 'GO' and len(self.trial_settings) > 3:
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

import numpy as np
from enthought.traits.api import HasTraits
from cns import choice

class CLControllerMixin(HasTraits):

    def _create_selector(self):
        # The selector is a generator function that yields values from a list
        # of elements. In this case, we initialize the selector (the
        # generator) with a list of TrialSetting instances. If we wish for a
        # certain parameter to be presented multiple times in a single set, we
        # need to repeat this parameter in the list.
        order = self.get_current_value('go_setting_order')
        settings = self.get_current_value('go_settings')
        if order is not None and settings is not None:
            selector = choice.options[order]
            expanded_settings = []
            for setting in settings:
                try:
                    repeats = setting.repeats
                except:
                    repeats = 1
                for i in range(repeats):
                    expanded_settings.append(setting.clone_traits())
            self.current_sequence = selector(expanded_settings)
    
    def next_setting(self):        
        # Must be able to handle both the initial (first trial) and repeat nogo
        # cases as needed.  Check for special cases first.
        if self.remind_requested:
            self.remind_requested = False
            return self.remind_setting()
        if len(self.model.data.trial_log) == 0:
            return self.initial_setting()

        # Now, check to see if we need to update the selector
        if self.current_sequence is None or \
                self.value_changed('go_setting_order') or \
                self.value_changed('go_settings'):
            self._create_selector()
        
        # This is a regular case.  Select the appropriate setting.
        spout = self.model.data.yes_seq[-1]
        nogo = self.model.data.nogo_seq[-1]
        if nogo and spout and self.get_current_value('repeat_fa'):
            return self.nogo_repeat_setting()
        if np.random.uniform() <= self.get_current_value('go_probability'):
            return self.current_sequence.next()
        else:
            return self.nogo_setting()

    def initial_setting(self):
        return self.remind_setting()
    
    def remind_setting(self):    
        return self.get_current_value('remind_setting')

    def nogo_setting(self):
        return self.get_current_value('nogo_setting')

    def nogo_repeat_setting(self):
        setting = self.get_current_value('nogo_setting').clone_traits()
        setting.ttype = 'NOGO_REPEAT'
        return setting

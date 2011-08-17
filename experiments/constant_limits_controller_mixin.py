import numpy as np
from enthought.traits.api import HasTraits, on_trait_change
from trial_setting import TrialSetting
from cns import choice
from copy import copy

class ConstantLimitsControllerMixin(HasTraits):

    def _get_old_list(self, new_list, new_element, name, old):
        old_list = new_list[:]
        index = old_list.index(new_element)
        old_element = copy(new_element)
        setattr(old_element, name, old)
        old_list[index] = old_element
        return old_list
        
    @on_trait_change('model.paradigm.go_settings:[+monitor, +context]')
    def notify(self, instance, name, old, new):
        new_list = self.model.paradigm.go_settings[:]
        old_list = self._get_old_list(new_list, instance, name, old)
        self.handle_change(self.model.paradigm, 'go_settings', old_list,
                new_list)
        
    def set_go_setting_order(self, value):
        self._create_selector()
        
    def set_go_settings(self, value):
        print "GO UPDATE", value
        self._create_selector()
        
    def _create_selector(self):
        # The selector is a generator function that yields values from a list of
        # elements.  In this case, we initialize the selector (the generator)
        # with a list of TrialSetting instances.  If we wish for a certain
        # parameter to be presented multiple times in a single set, we need to
        # repeat this parameter in the list.
        order = self.get_current_value('go_setting_order')
        settings = self.get_current_value('go_settings')
        if order is not None and settings is not None:
            selector = choice.options[order]
            expanded_settings = []
            for setting in settings:
                for i in range(setting.repeats):
                    new = TrialSetting()
                    new.copy_traits(setting)
                    expanded_settings.append(new)
            self.current_sequence = selector(expanded_settings)
    
    def initial_setting(self):
        return 'GO_REMIND', self.model.paradigm.remind_setting
    
    def next_setting(self):        
        spout = self.model.data.yes_seq[-1]
        nogo = self.model.data.nogo_seq[-1]
        
        if nogo and spout and self.get_current_value('repeat_fa'):
            return 'NOGO_REPEAT', self.get_current_value('nogo_setting')
        
        if np.random.uniform() <= self.get_current_value('go_probability'):
            return 'GO', self.current_sequence.next()
        else:
            return 'NOGO', self.get_current_value('nogo_setting')

    def remind_setting(self):    
        return 'GO_REMIND', self.get_current_value('remind_setting')

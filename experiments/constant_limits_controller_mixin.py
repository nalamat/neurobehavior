import numpy as np
from enthought.traits.api import HasTraits, on_trait_change, Bool
from cns import choice
from copy import copy

class ConstantLimitsControllerMixin(HasTraits):
    
    remind_requested = Bool(False)

    def set_go_setting_order(self, value):
        self._create_selector()
        
    def set_go_settings(self, value):
        self._create_selector()
        
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
                for i in range(setting.repeats):
                    expanded_settings.append(setting.clone_traits())
            self.current_sequence = selector(expanded_settings)
    
    def next_setting(self):        
        # Must be able to handle both the initial (first trial) and repeat
        # nogo cases as needed.  Check for special cases first.
        if self.remind_requested:
            self.remind_requested = False
            return self.remind_setting()
        if len(self.model.data.trial_log) == 0:
            return self.initial_setting()
        
        # This is a regular case.  Select the appropriate setting.
        spout = self.model.data.yes_seq[-1]
        nogo = self.model.data.nogo_seq[-1]
        if nogo and spout and self.get_current_value('repeat_fa'):
            return 'NOGO_REPEAT', self.get_current_value('nogo_setting')
        if np.random.uniform() <= self.get_current_value('go_probability'):
            return 'GO', self.current_sequence.next()
        else:
            return 'NOGO', self.get_current_value('nogo_setting')

    def initial_setting(self):
        return 'GO_REMIND', self.model.paradigm.remind_setting
    
    def remind_setting(self):    
        return 'GO_REMIND', self.get_current_value('remind_setting')
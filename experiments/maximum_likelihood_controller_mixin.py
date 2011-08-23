from functools import partial
import numpy as np
from enthought.traits.api import HasTraits, Int, Enum
#from .trial_setting import TrialSetting
from .maximum_likelihood import MaximumLikelihood, p_yes

class MaximumLikelihoodControllerMixin(HasTraits):
    
    current_mode = Enum('adaptive', 'static')
    
    def set_fa_rate(self, value):
        self._reset_tracker()
    
    def set_midpoint(self, value):
        self._reset_tracker()
        
    def set_slope(self, value):
        self._reset_tracker()
        
    def set_tracks(self, value):
        self.current_num_tracks = len(value)
        self.current_tracks = value
        self.current_track = 0
        
    def _evaluate_track(self, track):
        current_guess = self.model.data.ml_coefficients
        ml = self.model.data.ml
        context = { 'sweetpoint': ml.sweetpoint(*current_guess),
                    'p_yes': partial(p_yes, *current_guess) }
        return eval(track.setting, context, {})
       
    def _reset_tracker(self):
        a = self.get_current_value('fa_rate')
        m = self.get_current_value('midpoint')
        k = self.get_current_value('slope')
        self.model.data.ml = MaximumLikelihood(a, m, k)
        ml_coefficients = self.model.data.ml_coefficients
        if ml_coefficients is not None:
            self.model.data.ml_coefficients_history.append(ml_coefficients)
    
    def initial_setting(self):
        #return 'GO', TrialSetting(self.model.paradigm.initial_setting)
        return 'GO', (self.model.paradigm.initial_setting,)
    
    def _next_setting_adaptive(self):
        track = self.current_tracks[self.current_track]
        parameter = self._evaluate_track(track)
        self.current_track = (self.current_track+1) % self.current_num_tracks
        #return 'GO', TrialSetting(parameter)
        return 'GO', (parameter,)
        
    def _next_setting_static(self):
        parameter = self.get_current_value('remind_setting')
        #return 'GO_REMIND', TrialSetting(parameter)
        return 'GO_REMIND', (parameter,)
    
    def next_setting(self):
        # First check to see if last trial was a false alarm. If so, we should
        # repeat it if the user has requested this option.
        if self.model.data.fa_seq[-1] and self.get_current_value('repeat_fa'):
            parameter = self.get_current_value('nogo_setting')
            #return 'NOGO_REPEAT', TrialSetting(parameter)
            return 'NOGO_REPEAT', (parameter,)

        
        # Otherwise, determine if the next trial should be a go or nogo
        if np.random.uniform() <= self.get_current_value('go_probability'):
            if self.current_mode == 'adaptive':
                return self._next_setting_adaptive()
            else:
                return self._next_setting_static()
        else:
            #parameter = self.get_current_value('nogo_setting')
            #return 'NOGO', TrialSetting(parameter)
            return 'NOGO', (parameter,)

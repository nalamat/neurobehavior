from functools import partial
import numpy as np
from enthought.traits.api import HasTraits, Bool
from .maximum_likelihood import MaximumLikelihood
from .trial_setting import TrialSetting

def percent_correct(a, m, k, p):
    '''
    Given the guess coefficients, return the stimulus level most likely to
    achieve the given p value
    '''
    return (np.log((1-a)/(p-a)-1)/-k)+m

class MLControllerMixin(HasTraits):
    
    remind_requested = Bool(False)
    
    def set_ml_fa_rate(self, value):
        self._reset_tracker()
    
    def set_ml_midpoint(self, value):
        self._reset_tracker()
        
    def set_ml_slope(self, value):
        self._reset_tracker()
        
    def set_tracks(self, value):
        self.current_num_tracks = len(value)
        self.current_tracks = value
        self.current_track = 0
        
    def _evaluate_track(self, track):
        current_guess = self.model.data.ml_coefficients
        ml = self.model.data.ml
        context = { 'sweetpoint': ml.sweetpoint(*current_guess),
                    'percent_correct': partial(percent_correct, *current_guess)
                  }
        return eval(track, context, {})
       
    def _initialize_tracker(self):
        a = self.model.paradigm.ml_fa_rate.evaluate()
        m = self.model.paradigm.ml_midpoint.evaluate()
        k = self.model.paradigm.ml_slope.evaluate()
        self.model.data.ml = MaximumLikelihood(a, m, k)
        self.model.paradigm._finalized = True
        ml_coefficients = self.model.data.ml_coefficients
        if ml_coefficients is not None:
            self.model.data.ml_coefficients_history.append(ml_coefficients)
    
    # Some paradigms may wish to override the initial setting.  This makes it
    # easy.
    def initial_setting(self):
        setting = self.get_current_value('initial_setting') 
        return TrialSetting('GO_REMIND', setting)
    
    def next_setting(self):
        if not self.model.paradigm._finalized:
            self._initialize_tracker()

        # A reminder request overrides all other options here
        if self.remind_requested:
            self.remind_requested = False
            setting = self.get_current_value('remind_setting')
            return TrialSetting('GO_REMIND', setting)

        if len(self.model.data.trial_log) == 0:
            return self.initial_setting()

        # Next check to see if last trial was a false alarm. If so, we should
        # repeat it if the user has requested this option.
        if self.model.data.fa_seq[-1] and self.get_current_value('repeat_fa'):
            parameter = self.get_current_value('nogo_setting')
            return TrialSetting('NOGO_REPEAT', parameter)

        # Otherwise, determine if the next trial should be a go or nogo
        if np.random.uniform() <= self.get_current_value('go_probability'):
            if self.model.data.guess_initialized:
                track = self.current_tracks[self.current_track]
                parameter = self._evaluate_track(track)
                self.current_track = (self.current_track+1) % self.current_num_tracks
            else:
                # The estimator has not been initialized, so we need to continue
                # using the initial_setting.
                parameter = self.get_current_value('initial_setting')
            return TrialSetting('GO', parameter)

        # If we reach this point, it's a nogo
        return TrialSetting('NOGO', self.get_current_value('nogo_setting'))

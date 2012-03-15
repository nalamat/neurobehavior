import numpy as np
from enthought.traits.api import HasTraits, Float, Instance, Property, Array,\
     on_trait_change, cached_property, Tuple, List
from .maximum_likelihood import MaximumLikelihood

class MaximumLikelihoodDataMixin(HasTraits):
    
    ml = Instance(MaximumLikelihood)
    ml_coefficients = Tuple(Float, Float, Float)
    ml_par_seq = Property(Array('f'), depends_on='trial_log')
    ml_hit_seq = Property(Array('b'), depends_on='trial_log')
    ml_coefficients_history = List(Tuple(Float, Float, Float))
    
    @cached_property
    def _get_ml_par_seq(self):
        try:
            return np.array([e[0] for e in self.par_seq[self.go_seq]])
        except IndexError:
            return np.array([])

    @cached_property
    def _get_ml_hit_seq(self):
        try:
            return self.hit_seq[self.go_seq]
        except IndexError:
            return np.array([], dtype='bool')
    
    @on_trait_change('trial_log')
    def _update_ml(self):
        if self.go_seq[-1]:
            last_parameter = self.par_seq[-1]
            last_response = self.yes_seq[-1]
            self.ml.update_estimate(last_parameter, last_response)
            self.ml_coefficients = self.ml.best_coefficients()
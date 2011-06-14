from numpy import clip
from scipy.stats import norm
from enthought.traits.api import HasTraits, Float, Property, List, \
    cached_property

class SDTDataMixin(HasTraits):

    # Clip FA/HIT rate if < clip or > 1-clip (prevents unusually high z-scores)
    clip            = Property(store='attribute')

    @cached_property
    def _get_clip(self):
        return 0.05

    z_fa            = Property(Float,       depends_on='global_fa_frac')
    par_z_fa        = Property(List(Float), depends_on='par_fa_frac')
    par_z_hit       = Property(List(Float), depends_on='par_hit_frac')
    par_dprime      = Property(List(Float), depends_on='par_z_hit, par_z_fa')
    par_criterion   = Property(List(Float), depends_on='par_z_hit, par_z_fa')

    @cached_property
    def _get_par_z_hit(self):
        par_hit_frac = clip(self.par_hit_frac, self.clip, 1-self.clip)
        return norm.ppf(par_hit_frac)

    @cached_property
    def _get_par_z_fa(self):
        par_fa_frac = clip(self.par_fa_frac, self.clip, 1-self.clip)
        return norm.ppf(par_fa_frac)

    @cached_property
    def _get_par_dprime(self):
        return self.par_z_hit-self.z_fa

    @cached_property
    def _get_z_fa(self):
        global_fa_frac = clip(self.global_fa_frac, self.clip, 1-self.clip)
        return norm.ppf(global_fa_frac)

    def _get_par_criterion(self):
        return -0.5*(self.par_z_hit+self.z_fa)

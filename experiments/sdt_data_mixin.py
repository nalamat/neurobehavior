from numpy import clip, isnan
from scipy.stats import norm
from traits.api import HasTraits, Float, Property, List, \
    cached_property

class SDTDataMixin(HasTraits):

    # Clip FA/HIT rate if < clip or > 1-clip (prevents unusually high z-scores)

    clip            = Property(store='attribute')

    @cached_property
    def _get_clip(self):
        return 0.05

    z_fa            = Property(Float,       depends_on='global_fa_frac')
    par_z_fa        = Property(List(Float), depends_on='par_fa_frac')

    par_z_hit       = Property(depends_on='par_hit_frac',
                               cl_statistic=True,
                               abbreviated_label='Z Hit',
                               label='Z-score of hit fraction',
                               expected_range=(-3, 3),
                               suggested_grid=(0.2, 1))

    par_dprime      = Property(depends_on='par_z_hit, par_z_fa',
                               cl_statistic=True,
                               par_info_label='d',
                               abbreviated_label='d\'',
                               label='d prime',
                               expected_range=(-1, 4),
                               suggested_grid=(0.2, 1))

    par_criterion   = Property(List(Float), depends_on='par_z_hit, par_z_fa')

    @cached_property
    def _get_par_z_hit(self):
        par_hit_frac = clip(self.par_hit_frac, self.clip, 1-self.clip)
        return norm.ppf(par_hit_frac)

    @cached_property
    def _get_par_dprime(self):
        return self.par_z_hit-self.z_fa

    @cached_property
    def _get_z_fa(self):
        fa_frac = clip(self.global_fa_frac, self.clip, 1-self.clip)
        if isnan(fa_frac):
            fa_frac = self.clip
        return norm.ppf(fa_frac)

    def _get_par_criterion(self):
        return -0.5*(self.par_z_hit+self.z_fa)

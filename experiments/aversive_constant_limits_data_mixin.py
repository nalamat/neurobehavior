from enthought.traits.api import HasTraits, Property, cached_property
import numpy as np

class AversiveConstantLimitsDataMixin(HasTraits):

    par_warn_count  = Property(depends_on='masked_trial_log, parameters',
                               cl_statistic=True,
                               par_info_label='warn',
                               abbreviated_label='Warn #',
                               label='Warn count',
                               expected_range=(0, 'auto'),
                               suggested_grid=(1, 5))

    par_safe_count = Property(depends_on='masked_trial_log, parameters',
                               cl_statistic=True,
                               par_info_label='safe',
                               abbreviated_label='Safe #',
                               label='Safe count',
                               expected_range=(0, 'auto'),
                               suggested_grid=(1, 5))

    par_hit_count   = Property(depends_on='masked_trial_log, parameters',
                               cl_statistic=True,
                               par_info_label='hit',
                               abbreviated_label='Hit #',
                               label='Hit count',
                               expected_range=(0, 'auto'),
                               suggested_grid=(1, 5))

    par_miss_count  = Property(depends_on='masked_trial_log, parameters',
                               cl_statistic=True,
                               par_info_label='miss',
                               abbreviated_label='Miss #',
                               label='Miss count',
                               expected_range=(0, 'auto'),
                               suggested_grid=(1, 5))

    par_fa_count    = Property(depends_on='masked_trial_log, parameters',
                               cl_statistic=True,
                               par_info_label='fa',
                               abbreviated_label='FA #',
                               label='False alarm count',
                               expected_range=(0, 'auto'),
                               suggested_grid=(1, 5))

    par_cr_count    = Property(depends_on='masked_trial_log, parameters',
                               cl_statistic=True,
                               par_info_label='cr',
                               abbreviated_label='CR #',
                               label='Correct reject count',
                               expected_range=(0, 'auto'),
                               suggested_grid=(1, 5))

    par_hit_frac    = Property(depends_on='masked_trial_log, parameters',
                               cl_statistic=True,
                               par_info_label='hit_frac',
                               abbreviated_label='Hit %',
                               label='Hit fraction',
                               expected_range=(0, 1),
                               suggested_grid=(0.05, 0.2))

    # Summary table containing most of the statistics
    par_info = Property(store='table', depends_on='masked_trial_log')

    @cached_property
    def _get_par_fa_count(self):
        return self.apply_par_mask(np.sum, self.fa_seq)

    @cached_property
    def _get_par_cr_count(self):
        return self.apply_par_mask(np.sum, self.cr_seq)

    @cached_property
    def _get_par_hit_count(self):
        return self.apply_par_mask(np.sum, self.hit_seq)

    @cached_property
    def _get_par_miss_count(self):
        return self.apply_par_mask(np.sum, self.miss_seq)

    @cached_property
    def _get_par_warn_count(self):
        return self.apply_par_mask(np.sum, self.warn_seq)

    @cached_property
    def _get_par_safe_count(self):
        return self.apply_par_mask(np.sum, self.safe_seq)

    @cached_property
    def _get_par_hit_frac(self):
        return self.par_hit_count/self.par_warn_count

    @cached_property
    def _get_par_info(self):
        data = {
                'safe_count':       self.par_safe_count,
                'warn_count':       self.par_warn_count,
                'fa_count':         self.par_fa_count,
                'cr_count':         self.par_cr_count,
                'hit_count':        self.par_hit_count,
                'miss_count':       self.par_miss_count,
                'hit_frac':         self.par_hit_frac,
                'dprime':           self.par_dprime,
                'criterion':        self.par_criterion,

                # Duplicates required to work with par_info_label of
                # constant limits mixin
                'safe':             self.par_safe_count,
                'warn':             self.par_warn_count,
                'fa':               self.par_fa_count,
                'cr':               self.par_cr_count,
                'hit':              self.par_hit_count,
                'miss':             self.par_miss_count,
                'd':                self.par_dprime,
                }
        for i, parameter in enumerate(self.parameters):
            data[parameter] = [p[i] for p in self.pars]
        return np.rec.fromarrays(data.values(), names=data.keys())

    PLOT_VALUES = ('par_warn_count', 'par_hit_frac', 'par_dprime')

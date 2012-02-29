from __future__ import division

import numpy as np
from scipy import stats
from enthought.traits.api import (HasTraits, Property, cached_property,
        on_trait_change)

class PositiveConstantLimitsDataMixin(HasTraits):

    par_go_mask     = Property(depends_on='masked_trial_log, parameters')

    @cached_property
    def _get_par_go_mask(self):
        return [self.go_seq & m for m in self.par_mask]

    par_go_count    = Property(depends_on='masked_trial_log, parameters',
                               cl_statistic=True,
                               par_info_label='go',
                               abbreviated_label='Go #',
                               label='Go count',
                               expected_range=(0, 'auto'),
                               suggested_grid=(1, 5))

    par_nogo_count  = Property(depends_on='masked_trial_log, parameters',
                               cl_statistic=True,
                               par_info_label='nogo',
                               abbreviated_label='Nogo #',
                               label='Nogo count',
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

    @cached_property
    def _get_par_go_count(self):
        return self.par_hit_count+self.par_miss_count

    @cached_property
    def _get_par_nogo_count(self):
        return self.par_fa_count+self.par_cr_count

    @cached_property
    def _get_par_hit_count(self):
        return self.apply_par_mask(np.sum, self.hit_seq)

    @cached_property
    def _get_par_miss_count(self):
        return self.apply_par_mask(np.sum, self.miss_seq)

    @cached_property
    def _get_par_fa_count(self):
        return self.apply_par_mask(np.sum, self.fa_seq)

    @cached_property
    def _get_par_cr_count(self):
        return self.apply_par_mask(np.sum, self.cr_seq)

    @cached_property
    def _get_par_hit_frac(self):
        return self.par_hit_count/(self.par_hit_count+self.par_miss_count)

    @on_trait_change('par_dprime')
    def fire_data_changed(self):
        self.data_changed = True

    par_go_nogo_ratio = Property(depends_on='masked_trial_log, parameters')

    @cached_property
    def _get_par_go_nogo_ratio(self):
        return self.par_go_count/self.par_nogo_count

    par_mean_reaction_time      = Property(depends_on='masked_trial_log, parameters')
    par_mean_response_time      = Property(depends_on='masked_trial_log, parameters')
    par_median_reaction_time    = Property(depends_on='masked_trial_log, parameters')
    par_median_response_time    = Property(depends_on='masked_trial_log, parameters')
    par_std_reaction_time       = Property(depends_on='masked_trial_log, parameters')
    par_std_response_time       = Property(depends_on='masked_trial_log, parameters')

    def _get_par_mean_reaction_time(self):
        return self.apply_mask(stats.nanmean, self.par_go_mask,
                self.react_time_seq)

    def _get_par_mean_response_time(self):
        return self.apply_mask(stats.nanmean, self.par_go_mask,
                self.resp_time_seq)

    def _get_par_median_reaction_time(self):
        return self.apply_mask(stats.nanmedian, self.par_go_mask,
                self.react_time_seq)

    def _get_par_median_response_time(self):
        return self.apply_mask(stats.nanmedian, self.par_go_mask,
                self.resp_time_seq)

    def _get_par_std_reaction_time(self):
        return self.apply_mask(stats.nanstd, self.par_go_mask,
                self.react_time_seq)

    def _get_par_std_response_time(self):
        return self.apply_mask(stats.nanstd, self.par_go_mask,
                self.resp_time_seq)

    par_info = Property(store='table', depends_on='par_dprime')

    @cached_property
    def _get_par_info(self):
        data = {
                'parameter':     [repr(p).strip(',()') for p in self.pars],
                'hit_frac':      self.par_hit_frac,
                'd':             self.par_dprime,
                'criterion':     self.par_criterion,
                'go':            self.par_go_count,
                'nogo':          self.par_nogo_count,
                'go_nogo_ratio': self.par_go_nogo_ratio,
                'hit':           self.par_hit_count,
                'miss':          self.par_miss_count,
                'fa':            self.par_fa_count,
                'cr':            self.par_cr_count,
                'mean_react':    self.par_mean_reaction_time,
                'mean_resp':     self.par_mean_response_time,
                'median_react':  self.par_median_response_time,
                'median_resp':   self.par_median_response_time,
                'std_react':     self.par_std_reaction_time,
                'std_resp':      self.par_std_response_time,
                }
        for i, parameter in enumerate(self.parameters):
            data[parameter] = [p[i] for p in self.pars]
        return np.rec.fromarrays(data.values(), names=data.keys())

    PLOT_VALUES = ('par_go_count', 'par_hit_frac', 'par_dprime')

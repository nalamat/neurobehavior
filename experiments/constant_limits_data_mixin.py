from __future__ import division

import numpy as np
from scipy import stats
from enthought.traits.api import (HasTraits, Property, cached_property,
        on_trait_change, List, Float)

class ConstantLimitsDataMixin(HasTraits):

    par_go_mask     = Property(depends_on='masked_trial_log, parameters')

    @cached_property
    def _get_par_go_mask(self):
        return [self.go_seq & m for m in self.par_mask]

    par_go_count    = Property(depends_on='masked_trial_log, parameters')
    par_nogo_count  = Property(depends_on='masked_trial_log, parameters')

    @cached_property
    def _get_par_go_count(self):
        return self.par_hit_count+self.par_miss_count

    @cached_property
    def _get_par_nogo_count(self):
        return self.par_fa_count+self.par_cr_count

    par_hit_count   = Property(depends_on='masked_trial_log, parameters')
    par_miss_count  = Property(depends_on='masked_trial_log, parameters')
    par_fa_count    = Property(depends_on='masked_trial_log, parameters')
    par_cr_count    = Property(depends_on='masked_trial_log, parameters')

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

    par_hit_frac = Property(List(Float), depends_on='masked_trial_log, parameters')

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

    available_statistics = {
            'par_cr_count': 'Correct rejects',
            'par_fa_count': 'False alarms',
            'par_hit_count': 'Hits',
            'par_miss_count': 'Misses',
            'par_go_count': 'GO trials',
            'par_nogo_count': 'NOGO trials',
            'par_dprime': 'd\'',
            'par_criterion': 'C',
            'par_hit_frac': 'Hit fraction',
            'par_mean_reaction_time': 'Mean reaction time',
            'par_mean_response_time': 'Mean response time',
            }

    PLOT_RANGE_HINTS = {
                'par_cr_count'      : {'low_setting': 0, 'high_setting': 'auto'},
                'par_fa_count'      : {'low_setting': 0, 'high_setting': 'auto'},
                'par_hit_count'     : {'low_setting': 0, 'high_setting': 'auto'},
                'par_miss_count'    : {'low_setting': 0, 'high_setting': 'auto'},
                'par_go_count'      : {'low_setting': 0, 'high_setting': 'auto'},
                'par_nogo_count'    : {'low_setting': 0, 'high_setting': 'auto'},
                'par_dprime'        : {'low_setting': -1, 'high_setting': 3},
                'par_criterion'     : {'low_setting': -2, 'high_setting': 2},
                'par_hit_frac'      : {'low_setting': 0, 'high_setting': 1},
                'par_mean_reaction_time': {'low_setting': 0, 'high_setting': 'auto'},
                'par_mean_response_time': {'low_setting': 0, 'high_setting': 'auto'},
                }

    PLOT_GRID_HINTS = {
                'par_cr_count'      : {'major_value': 5, 'minor_value': 1},
                'par_fa_count'      : {'major_value': 5, 'minor_value': 1},
                'par_hit_count'     : {'major_value': 5, 'minor_value': 1},
                'par_miss_count'    : {'major_value': 5, 'minor_value': 1},
                'par_go_count'      : {'major_value': 5, 'minor_value': 1},
                'par_nogo_count'    : {'major_value': 5, 'minor_value': 1},
                'par_dprime'        : {'major_value': 1, 'minor_value': 0.25},
                'par_criterion'     : {},
                'par_hit_frac'      : {'major_value': 0.2, 'minor_value': 0.05},
                'par_mean_reaction_time': {'major_value': 1, 'minor_value': 0.025},
                'par_mean_response_time': {'major_value': 1, 'minor_value': 0.025},
                }

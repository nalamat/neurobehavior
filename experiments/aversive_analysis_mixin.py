from __future__ import division

import numpy as np
from matplotlib import mlab

from enthought.traits.api import (Int, HasTraits, Range, Float, Enum,
        cached_property, Property)

from sdt_data_mixin import SDTDataMixin

class AversiveAnalysisMixin(SDTDataMixin):
    '''
    Scored aversive data

    False alarms and hits can only be determined after we score the data.  Prior
    to scoring the data, we must decide what trials need to be excluded: e.g.
    the subject may have been inattentive in the beginning or have grown bored
    with the task towards the end. 

    Scores contains the actual contact ratio for each trial.  False alarms and
    hits are then computed against these scores (using the contact_fraction as
    the threshold).  Scores are a fraction (0 ot 1) indicating degree of
    animal's contact with spout during the check period defined by
    `contact_offset` and `contact_dur` (relative to the trial timestamp).

    Parameters
    ----------
    exclude_first : int
        Number of trials at beginning to ignore
    exclude_last : int
        Number trials at end to ignore
    contact_offset : float (seconds)
        Start of check period relative to trial timestamp, can be a negative
        value
    contact_dur : float (seconds)
        Duration of check period
    reaction_offset : float (seconds)
        Start of snippet to extract relative to trial timestamp, can be a
        negative value
    reaction_dur : float (seconds)
        Duration of snippet to extract

    Computed properties
    -------------------
    masked_trial_log : record array
        Trial log (as record array) with trials excluded
    contact scores : array_like
        Fraction of check period that subject was in contact with spout
    contact_seq : array_like
        True/False sequence indicating whether animal was in contact with the
        spout during the check period based on `contact_fraction`.
    '''

    # Mask parameters
    mask_mode = Enum('none', 'exclude', 'include', store='attribute')
    exclude_first = Int(0, store='attribute')
    exclude_last = Int(0, store='attribute')
    include_last = Int(0, store='atribute')

    # Analysis parameters
    contact_offset = Float(0.9, store='attribute')
    contact_dur = Float(0.1, store='attribute')
    contact_fraction = Range(0.0, 1.0, 0.5, store='attribute')
    contact_reference = Enum('trial start', 'trial end')

    reaction_offset = Float(-1, store='attribute')
    reaction_dur = Float(3.0, store='attribute')

    # Basic analysis of masked data
    contact_scores = Property(store='array', dtype='f',
            depends_on='trial_log, contact_dur, contact_offset')
    on_spout_seq = Property(depends_on='trial_log')
    off_spout_seq = Property(depends_on='trial_log')
    fa_seq = Property(depends_on='trial_log')
    cr_seq = Property(depends_on='trial_log')
    hit_seq = Property(depends_on='trial_log')
    miss_seq = Property(depends_on='trial_log')
    par_cr_count = Property(depends_on='trial_log')
    par_fa_count = Property(depends_on='trial_log')
    par_miss_count = Property(depends_on='trial_log')
    par_hit_count = Property(depends_on='trial_log')
    par_safe_count = Property(depends_on='trial_log')
    par_warn_count = Property(depends_on='trial_log')
    par_hit_frac = Property(depends_on='trial_log')
    par_fa_frac = Property(depends_on='trial_log')
    global_fa_frac = Property(depends_on='trial_log')

    # Summary table containing most of the statistics
    par_info = Property(store='table', depends_on='trial_log')

    #contact_scores = List

    #@on_trait_change('new_trial')
    #def compute_contact_score(self, trial_data):
    #    contact = self.contact_digital
    #    offset = self.contact_offset
    #    dur = self.contact_dur
    #    if self.contact_reference == 'trial start':
    #        ts = trial_data['ts_start']
    #    else:
    #        ts = trial_data['ts_end']
    #    score = contact.summarize(ts, offset, dur, np.mean)
    #    self.contact_scores.append(score)

    #@on_trait_change('contact_ddur, contact_offset')
    #def compute_contact_scores(self):
    #    contact = self.contact_digital
    #    offset = self.contact_offset
    #    dur = self.contact_dur
    #    if self.contact_reference == 'trial start':
    #        ts = trial_data['ts_start']
    #    else:
    #        ts = trial_data['ts_end']
    #    score = contact.summarize(ts, offset, dur, np.mean)
    #    self.contact_scores.append(score)


    @cached_property
    def _get_contact_scores(self):
        if self.contact_reference == 'trial start':
            timestamps = self.ts_start_seq
        else:
            timestamps = self.ts_end_seq
        return self.contact_digital.summarize(timestamps, self.contact_offset,
                self.contact_dur, np.mean)

    @cached_property
    def _get_on_spout_seq(self):
        return self.contact_scores >= self.contact_fraction

    @cached_property
    def _get_off_spout_seq(self):
        return self.contact_scores < self.contact_fraction

    @cached_property
    def _get_fa_seq(self):
        return self.safe_seq & self.off_spout_seq

    @cached_property
    def _get_cr_seq(self):
        return self.safe_seq & self.on_spout_seq

    @cached_property
    def _get_hit_seq(self):
        return self.warn_seq & self.off_spout_seq

    @cached_property
    def _get_miss_seq(self):
        return self.warn_seq & self.on_spout_seq

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
    def _get_par_fa_frac(self):
        return self.par_fa_count/self.par_safe_count

    @cached_property
    def _get_par_hit_frac(self):
        return self.par_hit_count/self.par_warn_count

    @cached_property
    def _get_global_fa_frac(self):
        fa = np.sum(self.fa_seq)
        cr = np.sum(self.cr_seq)
        return fa/(fa+cr)

    @cached_property
    def _get_par_info(self):
        data = {
                'parameter':        [repr(p).strip(',()') for p in self.pars],
                'safe_count':       self.par_safe_count,
                'warn_count':       self.par_warn_count,
                'fa_count':         self.par_fa_count,
                'hit_count':        self.par_hit_count,
                'hit_frac':         self.par_hit_frac,
                'fa_frac':          self.par_fa_frac,
                'dprime':           self.par_dprime,
                'criterion':        self.par_criterion,
                }
        for i, parameter in enumerate(self.parameters):
            data[parameter] = [p[i] for p in self.pars]
        return np.rec.fromarrays(data.values(), names=data.keys())

    summary_trial_log = Property(depends_on='trial_log')

    def _get_summary_trial_log(self):
        return self.trial_log[::-1]
        #try:
        #    trial_log = mlab.rec_append_fields(self.trial_log, 
        #            ('parameter', 'contact_score', 'on_spout'), 
        #            (self.par_seq, self.contact_scores, self.on_spout_seq))
        #    return trial_log[::-1]
        #except:
        #    return np.array([])

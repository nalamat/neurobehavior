from __future__ import division

import numpy as np
from matplotlib import mlab

from traits.api import (Int, HasTraits, Range, Float, Enum,
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

    # Analysis parameters
    contact_offset = Float(0.9)
    contact_dur = Float(0.1)
    contact_fraction = Range(0.0, 1.0, 0.5)
    contact_reference = Enum('trial start', 'trial end')

    # Basic analysis of masked data
    contact_scores = Property(depends_on='trial_log, contact_dur, contact_offset')
    on_spout_seq = Property(depends_on='trial_log')
    off_spout_seq = Property(depends_on='trial_log')
    fa_seq = Property(depends_on='trial_log')
    cr_seq = Property(depends_on='trial_log')
    hit_seq = Property(depends_on='trial_log')
    miss_seq = Property(depends_on='trial_log')
    global_fa_frac = Property(depends_on='trial_log')

    go_seq = Property(depends_on='trial_log')
    nogo_seq = Property(depends_on='trial_log')
    yes_seq = Property(depends_on='trial_log')

    @cached_property
    def _get_yes_seq(self):
        return self.on_spout_seq

    @cached_property
    def _get_nogo_seq(self):
        return self.safe_seq

    @cached_property
    def _get_go_seq(self):
        return self.warn_seq

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
    def _get_global_fa_frac(self):
        try:
            fa = np.sum(self.fa_seq)
            cr = np.sum(self.cr_seq)
            return fa/(fa+cr)
        except ZeroDivisionError:
            return np.nan

    def _get_summary_trial_log(self):
        return self.trial_log[::-1]

    summary_trial_log = Property(depends_on='trial_log')

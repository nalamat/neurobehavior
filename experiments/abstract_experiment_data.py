from __future__ import division

import logging
log = logging.getLogger(__name__)

import numpy as np
import pandas as pd
from scipy.stats import norm

from traits.api import (Instance, List, Property, Tuple, cached_property, Any,
                        Int, Event, HasTraits)

from cns.channel import FileChannel


class AbstractExperimentData(HasTraits):

    # Node to store the data in
    store_node = Any

    # List of parameters to analyze.  If you set this up properly, then you can
    # re-analyze your data on the fly.
    parameters = List(['to_duration'])

    trial_log = Instance('pandas.DataFrame', ())
    trial_log_updated = Event

    event_log = Any
    event_log_updated = Event

    performance = Instance('pandas.DataFrame')

    def _event_log_default(self):
        fh = self.store_node._v_file
        description = np.dtype([('ts', np.float64), ('event', 'S512')])
        node = fh.createTable(self.store_node, 'event_log', description)
        return node

    def log_event(self, ts, event):
        # The append() method of a tables.Table class requires a list of rows
        # (i.e. records) to append to the table.  Since we only append a single
        # row at a time, we need to nest it as a list that contains a single
        # record.
        self.event_log.append([(ts, event)])
        self.event_log_updated = ts, event

    def log_trial(self, **kwargs):
        # This is a very inefficient implementation (appends require
        # reallocating information in memory).
        self.trial_log = self.trial_log.append(kwargs, ignore_index=True)
        self.update_performance(self.trial_log)
        self.trial_log_updated = kwargs

    def save(self):
        '''
        Called by stop_experiment when the stop button is pressed.  This is your
        chance to save relevant data.
        '''
        # Dump the trial log table
        fh = self.store_node._v_file
        if len(self.trial_log):
            fh.createTable(self.store_node, 'trial_log', self.trial_log)
        else:
            log.debug('No trials in the trial_log file!')

    microphone = Instance(FileChannel)

    def _microphone_default(self):
        return FileChannel(node=self.store_node, name='microphone',
                           dtype=np.float32)

    def update_performance(self, trial_log):
        # Compute hit rate, FA rate, z-score and d'
        response_types = ['HIT', 'MISS', 'FA', 'CR']
        grouping = self.parameters + ['score']
        counts = trial_log.groupby(grouping).size().unstack('score')
        counts = counts.reindex_axis(response_types, axis='columns').fillna(0)

        counts['trials'  ] = counts.sum(axis=1)
        counts['hit_rate'] = counts.HIT/(counts.HIT+counts.MISS)
        counts['fa_rate' ] = counts.FA /(counts.FA +counts.CR  )

        # Hit rate for no go is CR rate and FA rate for go is miss rate
        hit_nan = np.isnan(counts.hit_rate);
        fa_nan  = np.isnan(counts.fa_rate );
        counts.hit_rate[hit_nan] = 1-counts.fa_rate [hit_nan]
        counts.fa_rate [fa_nan ] = 1-counts.hit_rate[fa_nan ]

        # Clip hit and FA rates to 0.05 and 0.95 and calculate d' sensitivity by
        # substracting Z score of hit rate of each go condition from Z score of
        # FA rate of the sole no go condition. No go is assumed to be the last
        # condition in the list and always has a d' of zero
        clipped_rates = counts[['hit_rate', 'fa_rate']].clip(0.05, 0.95)
        z_score = clipped_rates.apply(norm.ppf)
        counts['z_score'] = z_score.hit_rate-z_score.fa_rate.values[-1]
        counts.z_score.values[-1] = 0

        # Compute median reaction time and response time
        median = trial_log.groupby(self.parameters) \
            [['reaction_time', 'response_time']].median().add_prefix('median_')

        self.performance = counts.join(median)

from __future__ import division

import logging
log = logging.getLogger(__name__)

import sys
import json
import traceback

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
    trial_log2 = Any

    event_log = Any
    event_log_updated = Event

    performance = Instance('pandas.DataFrame')
    performance2 = Any

    def _event_log_default(self):
        log.debug('Creating node "event_log" in HDF5')
        fh = self.store_node._v_file
        description = np.dtype([('ts', np.float64), ('event', 'S512')])
        node = fh.createTable(self.store_node, 'event_log', description)
        return node

    def log_event(self, ts, event):
        # The append() method of a tables.Table class requires a list of rows
        # (i.e. records) to append to the table.  Since we only append a single
        # row at a time, we need to nest it as a list that contains a single
        # record.
        log.debug('Logging event to HDF5')
        self.event_log.append([(ts, event)])
        self.event_log_updated = ts, event

    def _trial_log2_default(self):
        return None

    def _performance2_default(self):
        return None

    def log_trial(self, **kwargs):
        try:
            # This is a very inefficient implementation (appends require
            # reallocating information in memory).
            log.debug('Logging trial')
            self.trial_log = self.trial_log.append(kwargs, ignore_index=True)
            self.trial_log_updated = kwargs
            log.info('Trial log: %s', str(kwargs))

            # Update performance, i.e. hit rate, FA rate and d' sensitivtiy
            self.update_performance(self.trial_log)
            perf = self.performance.to_dict('list')
            # Index column that is usually target_level should be added manually
            perf[self.performance.index.name] = list(self.performance.index.values)
            log.info('Performance: %s', str(perf))

            # TODO: Since kwargs might have different fields after each trial,
            # find a way to store trial log dynamically in HFD5
            # If haven't done yet, create a table for saving trial log to the
            # HDF5 file and set the column names. Column names should not change
            # throughout a single session
            # if self.trial_log2 is None:
            #     desc = []
            #     for key, val in kwargs.iteritems():
            #         if type(val) is str or type(val) is unicode:
            #             desc.append((key, 'S512'))
            #         else:
            #             desc.append((key, type(val)))
            #     desc = np.dtype(desc)
            #     fh = self.store_node._v_file
            #     log.debug('Creating node "trial_log" in HDF5')
            #     self.trial_log2 = fh.createTable(self.store_node, 'trial_log', desc)
            # self.trial_log2.append([tuple(kwargs.values())])

            # If haven't done yet, create a table for saving performance to the
            # HDF5 file and set the column names. Column names should not change
            # throughout a single session
            # if self.performance2 is None:
            #     desc = []
            #     for key, val in perf.iteritems():
            #         if type(val[0]) is str or type(val) is unicode:
            #             desc.append((key, 'S512'))
            #         else:
            #             desc.append((key, type(val[0])))
            #     desc = np.dtype(desc)
            #     fh = self.store_node._v_file
            #     log.debug('Creating node "performance" in HDF5')
            #     self.performance2 = fh.createTable(self.store_node, 'performance', desc)
            # # Do not append, but override previous content of the table
            # rows = zip(*perf.values())
            # nrows = self.performance2.length
            # if not nrows == 0:
            #     self.performance2.modify_rows(start=0,stop=nrows,rows=rows[:nrows])
            # if len(rows) > nrows:
            #     self.performance2.append(rows[nrows:])
        except:
            log.error(traceback.format_exc())

    def save(self):
        '''
        Called by stop_experiment when the stop button is pressed.  This is your
        chance to save relevant data.
        '''
        # Dump the trial log table
        # fh = self.store_node._v_file
        # if len(self.trial_log):
        #     fh.createTable(self.store_node, 'trial_log', self.trial_log)
        # else:
        #     log.debug('No trials in the trial_log file!')
        pass

    microphone = Instance(FileChannel)

    def _microphone_default(self):
        return FileChannel(node=self.store_node, name='microphone',
                           dtype=np.float32)

    def update_performance(self, trial_log):
        log.debug('Updating performnace')
        # Compute hit rate, FA rate, z-score and d'
        response_types = ['HIT', 'MISS', 'FA', 'CR']
        grouping = self.parameters + ['score']
        counts = trial_log.groupby(grouping).size().unstack('score')
        counts = counts.reindex_axis(response_types, axis='columns').fillna(0)

        counts['trials'  ] = counts.sum(axis=1)
        counts['hit_rate'] = counts.HIT/(counts.HIT+counts.MISS)
        counts['fa_rate' ] = counts.FA /(counts.FA +counts.CR  )

        # Hit rate for no go is CR rate and FA rate for go is miss rate
        hit_nan = np.isnan(counts.loc[:,'hit_rate']);
        fa_nan  = np.isnan(counts.loc[:,'fa_rate']);
        counts.loc[hit_nan,'hit_rate'] = 1-counts.loc[hit_nan,'fa_rate' ]
        counts.loc[fa_nan ,'fa_rate' ] = 1-counts.loc[fa_nan ,'hit_rate']

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
        log.debug('Performance updated')

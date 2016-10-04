from __future__ import division

import pandas as pd
import numpy as np
from scipy.stats import norm

from traits.api import Instance
from cns.channel import Channel, FileChannel
from abstract_experiment_data import AbstractExperimentData
from traits.api import Instance
from cns.channel import FileChannel, FileMultiChannel

import logging
log = logging.getLogger(__name__)


class PositiveData(AbstractExperimentData):

    microphone = Instance(FileChannel)
    np = Instance(FileChannel)
    spout = Instance(FileChannel)
    channels = 16
    # ch1 = Instance(FileChannel)
    # raw = Instance(FileMultiChannel)

    def _microphone_default(self):
        return FileChannel(node=self.store_node, name='microphone',
                           dtype=np.float32)

    def _np_default(self):
        return FileChannel(node=self.store_node, name='np', dtype=np.float32)

    def _spout_default(self):
        return FileChannel(node=self.store_node, name='spout', dtype=np.float32)

    # def _ch1_default(self):
    #     return FileChannel(node=self.store_node, name='ch1', dtype=np.float32)
    #
    # def _raw_default(self):
    #     # return FileChannel(node=self.store_node, name='raw', dtype=np.float32)
    #     return FileMultiChannel(node=self.store_node, channels=self.channels,
    #                             name='raw', dtype=np.float32,
    #                             compression_type='lzo', compression_level=1,
    #                             use_shuffle=True, use_checksum=True)

    def update_performance(self, trial_log):
        # Compute hit rate, FA rate, z-score and d'
        #self.parameters = ['to_duration']
        response_types = ['HIT', 'MISS', 'FA', 'CR']
        grouping = self.parameters + ['score']
        counts = trial_log.groupby(grouping).size().unstack('score')
        counts = counts.reindex_axis(response_types, axis='columns').fillna(0)
        counts['trials'] = counts.sum(axis=1)
        counts['hit_rate'] = counts.HIT/(counts.HIT+counts.MISS)
        counts['fa_rate'] = counts.FA/(counts.FA+counts.CR)
        clipped_rates = counts[['hit_rate', 'fa_rate']].clip(0.05, 0.95)
        z_score = clipped_rates.apply(norm.ppf)
        counts['z_score'] = z_score.hit_rate-z_score.fa_rate

        # Compute median reaction time and response time
        median = trial_log.groupby(self.parameters) \
            [['reaction_time', 'response_time']].median().add_prefix('median_')

        self.performance = counts.join(median)

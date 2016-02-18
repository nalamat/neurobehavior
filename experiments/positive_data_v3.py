from __future__ import division

import pandas as pd
import numpy as np
from scipy.stats import norm

from traits.api import Instance
from cns.channel import FileChannel
from abstract_experiment_data import AbstractExperimentData
from traits.api import Instance
from cns.channel import FileChannel

import logging
log = logging.getLogger(__name__)


class PositiveData(AbstractExperimentData):

    microphone = Instance(FileChannel)

    def _microphone_default(self):
        return FileChannel(node=self.store_node, name='microphone',
                           dtype=np.float32)

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

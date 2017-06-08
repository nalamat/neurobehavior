from __future__ import division

import pandas as pd
import numpy as np
from traits.api import Instance

from cns.channel import Channel, FileChannel, EpochFile
from cns.data.h5_utils import get_or_append_node
from abstract_experiment_data import AbstractExperimentData

import logging
log = logging.getLogger(__name__)


class PositiveData(AbstractExperimentData):

    trace_node = Any
    epoch_node = Any

    def _trace_node(self):
        return get_or_append_node(self.store_node, 'trace')

    def _epoch_node(self):
        return get_or_append_node(self.store_node, 'epoch')

    speaker = Instance(FileChannel)
    mic     = Instance(FileChannel)
    poke    = Instance(FileChannel)
    spout   = Instance(FileChannel)

    def _speaker_default(self):
        return FileChannel(node=self.trace_node, name='speaker', dtype=np.float32)

    def _mic_default(self):
        return FileChannel(node=self.trace_node, name='mic'    , dtype=np.float32)

    def _poke_default(self):
        return FileChannel(node=self.trace_node, name='poke'   , dtype=np.float32)

    def _spout_default(self):
        return FileChannel(node=self.trace_node, name='spout'  , dtype=np.float32)

    poke_epoch    = Instance(EpochFile)
    spout_epoch   = Instance(EpochFile)
    target_epoch  = Instance(EpochFile)
    pump_epoch    = Instance(EpochFile)
    trial_epoch   = Instance(EpochFile)

    def _poke_epoch_default(self):
        return EpochFile(node=self.epoch_node, name='poke'   , dtype=np.float32)

    def _spout_epoch_default(self):
        return EpochFile(node=self.epoch_node, name='spout'  , dtype=np.float32)

    def _target_epoch_default(self):
        return EpochFile(node=self.epoch_node, name='target' , dtype=np.float32)

    def _pump_epoch_default(self):
        return EpochFile(node=self.epoch_node, name='pump'   , dtype=np.float32)

    def _trial_epoch_default(self):
        return EpochFile(node=self.epoch_node, name='trial'  , dtype=np.float32)

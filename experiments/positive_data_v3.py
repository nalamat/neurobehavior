from __future__ import division

import pandas as pd
import numpy as np
from traits.api import Instance, Any

from cns.channel import Channel, FileChannel, FileEpoch
from cns.data.h5_utils import get_or_append_node
from abstract_experiment_data import AbstractExperimentData

import logging
log = logging.getLogger(__name__)


class PositiveData(AbstractExperimentData):

    trace_node = Any
    epoch_node = Any

    def setup(self):
        self.speaker._buffer
        self.mic._buffer
        self.poke._buffer
        self.spout._buffer
        self.poke_epoch._buffer
        self.spout_epoch._buffer
        self.target_epoch._buffer
        self.trial_epoch._buffer

    def _trace_node_default(self):
        return get_or_append_node(self.store_node, 'trace')

    def _epoch_node_default(self):
        return get_or_append_node(self.store_node, 'epoch')

    speaker = Instance(FileChannel)
    mic     = Instance(FileChannel)
    poke    = Instance(FileChannel)
    spout   = Instance(FileChannel)

    def _speaker_default(self):
        log.debug('Creating trace node "speaker" in HDF5')
        return FileChannel(node=self.trace_node, name='speaker', dtype=np.float32)

    def _mic_default(self):
        log.debug('Creating trace node "mic" in HDF5')
        return FileChannel(node=self.trace_node, name='mic'    , dtype=np.float32)

    def _poke_default(self):
        log.debug('Creating trace node "poke" in HDF5')
        return FileChannel(node=self.trace_node, name='poke'   , dtype=np.float32)

    def _spout_default(self):
        log.debug('Creating trace node "spout" in HDF5')
        return FileChannel(node=self.trace_node, name='spout'  , dtype=np.float32)

    poke_epoch    = Instance(FileEpoch)
    spout_epoch   = Instance(FileEpoch)
    target_epoch  = Instance(FileEpoch)
    trial_epoch   = Instance(FileEpoch)

    def _poke_epoch_default(self):
        log.debug('Creating epoch node "poke" in HDF5')
        return FileEpoch(node=self.epoch_node, name='poke'  , fs=1, dtype=np.float32)

    def _spout_epoch_default(self):
        log.debug('Creating epoch node "spout" in HDF5')
        return FileEpoch(node=self.epoch_node, name='spout' , fs=1, dtype=np.float32)

    def _target_epoch_default(self):
        log.debug('Creating epoch node "target" in HDF5')
        return FileEpoch(node=self.epoch_node, name='target', fs=1, dtype=np.float32)

    def _trial_epoch_default(self):
        log.debug('Creating epoch node "trial" in HDF5')
        return FileEpoch(node=self.epoch_node, name='trial' , fs=1, dtype=np.float32)

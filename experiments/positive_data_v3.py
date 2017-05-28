from __future__ import division

import pandas as pd
import numpy as np

from traits.api import Instance
from cns.channel import Channel, FileChannel
from abstract_experiment_data import AbstractExperimentData
from traits.api import Instance
from cns.channel import FileChannel, FileMultiChannel

import logging
log = logging.getLogger(__name__)


class PositiveData(AbstractExperimentData):

    speaker    = Instance(FileChannel)
    microphone = Instance(FileChannel)
    np         = Instance(FileChannel)
    spout      = Instance(FileChannel)
    channels   = 16

    def _speaker_default(self):
       return FileChannel(node=self.store_node, name='speaker',
                          dtype=np.float32)

    def _microphone_default(self):
        return FileChannel(node=self.store_node, name='microphone',
                           dtype=np.float32)

    def _np_default(self):
        return FileChannel(node=self.store_node, name='np', dtype=np.float32)

    def _spout_default(self):
        return FileChannel(node=self.store_node, name='spout', dtype=np.float32)

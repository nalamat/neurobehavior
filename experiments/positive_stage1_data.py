from traits.api import Instance, Bool
from cns.channel import FileChannel
import numpy as np

from .abstract_experiment_data import AbstractExperimentData
from .utils import get_temp_mic_node

import logging
log = logging.getLogger(__name__)

class PositiveStage1Data(AbstractExperimentData):

    microphone = Instance(FileChannel)

    # If True, save to datafile otherwise use a temporary file for storing the
    # mic data.
    save_microphone = Bool(False)

    def _microphone_default(self):
        if self.save_microphone:
            node = self.store_node
        else:
            node = get_temp_mic_node()
        return FileChannel(node=node, name='microphone', dtype=np.float32)

    override_TTL = Instance(FileChannel)
    spout_TTL = Instance(FileChannel)
    pump_TTL = Instance(FileChannel)
    signal_TTL = Instance(FileChannel)
    free_run_TTL = Instance(FileChannel)

    def _override_TTL_default(self):
        return self._create_channel('override_TTL', np.bool)

    def _spout_TTL_default(self):
        return self._create_channel('spout_TTL', np.bool)

    def _pump_TTL_default(self):
        return self._create_channel('pump_TTL', np.bool)

    def _signal_TTL_default(self):
        return self._create_channel('signal_TTL', np.bool)

    def _free_run_TTL_default(self):
        return self._create_channel('free_run_TTL', np.bool)

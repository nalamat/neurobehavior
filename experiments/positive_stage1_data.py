from enthought.traits.api import Instance
from cns.channel import FileChannel
from cns.data.h5_utils import get_or_append_node
import numpy as np

from abstract_experiment_data import AbstractExperimentData

class PositiveStage1Data(AbstractExperimentData):

    def _create_channel(self, name, dtype):
        contact_node = get_or_append_node(self.store_node, 'contact')
        return FileChannel(node=contact_node, name=name, dtype=dtype)

    override_TTL = Instance(FileChannel, 
            store='channel', store_path='contact/override_TTL')
    spout_TTL = Instance(FileChannel, 
            store='channel', store_path='contact/spout_TTL')
    pump_TTL = Instance(FileChannel, 
            store='channel', store_path='contact/pump_TTL')
    signal_TTL = Instance(FileChannel, 
            store='channel', store_path='contact/signal_TTL')
    free_run_TTL = Instance(FileChannel, 
            store='channel', store_path='contact/free_run_TTL')

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

from cns.experiment.data.experiment_data import ExperimentData, AnalyzedData
from cns.channel import FileChannel
from enthought.traits.api import Instance, List, CFloat, Int, Float, Any, \
    Range, DelegatesTo, cached_property, on_trait_change, Array, Event, \
    Property, Undefined, Callable, Str, Enum, Bool
from datetime import datetime
import numpy as np
from cns.data.h5_utils import append_node, get_or_append_node
from cns.pipeline import deinterleave, broadcast
from scipy.stats import norm

def apply_mask(fun, seq, mask):
    seq = np.array(seq).ravel()
    return [fun(seq[m]) for m in mask]

LOG_DTYPE = [('timestamp', 'i'), ('name', 'S64'), ('value', 'S128'), ]

class PositiveData_0_1(ExperimentData):

    version = Float(0.0)
    latest_version = 0.1

    version = 0.2

    store_node = Any
    contact_fs = Float(500.0)

    contact_data = Any

    poke_TTL = Instance(FileChannel, 
            store='channel', store_path='contact/poke_TTL')
    spout_TTL = Instance(FileChannel, 
            store='channel', store_path='contact/spout_TTL')
    trial_TTL = Instance(FileChannel, 
            store='channel', store_path='contact/trial_TTL')
    score_TTL = Instance(FileChannel, 
            store='channel', store_path='contact/score_TTL')
    pump_TTL = Instance(FileChannel,
            store='channel', store_path='contact/pump_TTL')
    signal_TTL = Instance(FileChannel,
            store='channel', store_path='contact/signal_TTL')
    response_TTL = Instance(FileChannel,
            store='channel', store_path='contact/response_TTL')
    reward_TTL = Instance(FileChannel,
            store='channel', store_path='contact/reward_TTL')

    def _create_channel(self, name, dtype):
        contact_node = get_or_append_node(self.store_node, 'contact')
        return FileChannel(node=contact_node, fs=self.contact_fs,
                           name=name, dtype=dtype)

    def _poke_TTL_default(self):
        return self._create_channel('poke_TTL', np.bool)

    def _spout_TTL_default(self):
        return self._create_channel('spout_TTL', np.bool)

    def _trial_TTL_default(self):
        return self._create_channel('trial_TTL', np.bool)

    def _score_TTL_default(self):
        return self._create_channel('score_TTL', np.bool)

    def _pump_TTL_default(self):
        return self._create_channel('pump_TTL', np.bool)

    def _signal_TTL_default(self):
        return self._create_channel('signal_TTL', np.bool)

    def _response_TTL_default(self):
        return self._create_channel('response_TTL', np.bool)

    def _reward_TTL_default(self):
        return self._create_channel('reward_TTL', np.bool)


PositiveData = PositiveData_0_1

if __name__ == '__main__':
    pass

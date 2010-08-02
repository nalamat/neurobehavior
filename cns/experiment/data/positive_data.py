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

    '''
    touch_digital = Instance(FileChannel, 
            store='channel', store_path='contact/touch_digital')
    touch_digital_mean = Instance(FileChannel, 
            store='channel', store_path='contact/touch_digital_mean')
    touch_analog = Instance(FileChannel, 
            store='channel', store_path='contact/touch_analog')
    '''
    optical_digital = Instance(FileChannel, 
            store='channel', store_path='contact/optical_digital')
    optical_digital_mean = Instance(FileChannel, 
            store='channel', store_path='contact/optical_digital_mean')
    optical_analog = Instance(FileChannel, 
            store='channel', store_path='contact/optical_analog')
    trial_running = Instance(FileChannel, 
            store='channel', store_path='contact/trial_running')
    reward_running = Instance(FileChannel,
            store='channel', store_path='contact/reward_running')

    '''
    # Stores raw contact data from optical and electrical sensors as well as
    # whether a trial is running.
    def _contact_data_default(self):
        targets = [self.touch_digital,
                   self.touch_digital_mean,
                   self.optical_digital,
                   self.optical_digital_mean,
                   self.contact_digital,
                   self.contact_digital_mean,
                   self.trial_running, ]
        return deinterleave(targets)
    '''

    def _create_channel(self, name, dtype):
        contact_node = get_or_append_node(self.store_node, 'contact')
        return FileChannel(node=contact_node, fs=self.contact_fs,
                           name=name, dtype=dtype)

    '''
    def _touch_digital_default(self):
        return self._create_channel('touch_digital', np.bool)

    def _touch_digital_mean_default(self):
        return self._create_channel('touch_digital_mean', np.float32)

    def _touch_analog_default(self):
        return self._create_channel('touch_analog', np.float32)
    '''

    def _optical_digital_default(self):
        return self._create_channel('optical_digital', np.bool)

    def _optical_digital_mean_default(self):
        return self._create_channel('optical_digital_mean', np.float32)

    def _optical_analog_default(self):
        return self._create_channel('optical_analog', np.float32)

    def _trial_running_default(self):
        return self._create_channel('trial_running', np.bool)

    def _reward_running_default(self):
        return self._create_channel('reward_running', np.bool)

PositiveData = PositiveData_0_1

if __name__ == '__main__':
    pass

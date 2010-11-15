from __future__ import division

from cns.experiment.data.experiment_data import ExperimentData, AnalyzedData
from cns.channel import FileChannel
from enthought.traits.api import Instance, List, CFloat, Int, Float, Any, \
    Range, DelegatesTo, cached_property, on_trait_change, Array, Event, \
    Property, Undefined, Callable, Str, Enum, Bool, Int, Str, Tuple
from datetime import datetime
import numpy as np
from cns.data.h5_utils import append_node, get_or_append_node
from cns.pipeline import deinterleave, broadcast
from scipy.stats import norm

import logging
log = logging.getLogger(__name__)

# Score functions
ts = lambda TTL: np.flatnonzero(TTL)
edge_rising = lambda TTL: np.r_[0, np.diff(TTL.astype('i'))] == 1
edge_falling = lambda TTL: np.r_[0, np.diff(TTL.astype('i'))] == -1

def apply_mask(fun, seq, mask):
    seq = np.array(seq).ravel()
    return [fun(seq[m]) for m in mask]

LOG_DTYPE = [('timestamp', 'i'), ('name', 'S64'), ('value', 'S128'), ]

class PositiveDataStage1(ExperimentData):

    contact_fs = Float(500.0)

    def _create_channel(self, name, dtype):
        contact_node = get_or_append_node(self.store_node, 'contact')
        return FileChannel(node=contact_node, fs=self.contact_fs,
                           name=name, dtype=dtype)

    override_TTL = Instance(FileChannel, 
            store='channel', store_path='contact/override_TTL')
    spout_TTL = Instance(FileChannel, 
            store='channel', store_path='contact/spout_TTL')
    pump_TTL = Instance(FileChannel, 
            store='channel', store_path='contact/pump_TTL')

    def _override_TTL_default(self):
        return self._create_channel('override_TTL', np.bool)

    def _spout_TTL_default(self):
        return self._create_channel('spout_TTL', np.bool)

    def _pump_TTL_default(self):
        return self._create_channel('pump_TTL', np.bool)

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

    TRIAL_DTYPE = [('ts_start', 'i'), ('ts_end', 'i'), ('type', 'S4'),
                   ('response', 'S16'), ('reaction_time', 'i')]

    trial_log = List(Tuple(Int, Int, Str, Str, Int), store='table',
                     dtype=TRIAL_DTYPE)

    # Total GO trials presented
    num_go = Int(store='attribute')
    # Total GO trials where subject provided response
    num_go_response = Int(store='attribute')
    # Total NOGO trials presented
    num_nogo = Int(store='attribute')
    # Total NOGO trials where subject provided response
    num_nogo_response = Int(store='attribute')
    # Total false alarms
    num_fa = Int(store='attribute')
    # Total hits
    num_hit = Int(store='attribute')
    # num_fa/num_nogo
    fa_frac = Float(store='attribute')
    # num_hit/num_go
    hit_frac = Float(store='attribute')
    # num_fa/num_nogo_response
    response_fa_frac = Float(store='attribute')
    # num_hit/num_go_response
    response_hit_frac = Float(store='attribute')

    def log_trial(self, ts_start, ts_end, ttype):
        log.debug('Logging trial %s (%d, %d)', ttype, ts_start, ts_end)
        if self.poke_TTL.get_range_index(ts_start, ts_end).all():
            response = 'NO_WITHDRAW'
        elif self.spout_TTL.get_range_index(ts_start, ts_end).any():
            response = 'SPOUT'
        elif self.poke_TTL.get_index(ts_end) == 1:
            response = 'POKE'
        else:
            response = 'NO_RESPONSE'

        #if response == 'SPOUT':
        #    spout = self.spout_TTL.get_range_index(ts_start, ts_end)
        #    rt = ts(edge_rising(spout))[0]
        #elif response == 'POKE':
        #    poke = self.poke_TTL.get_range_index(ts_start, ts_end)
        #    rt = ts(edge_rising(poke))[0]
        #else:
        #    rt = -1
        rt = -1

        self.trial_log.append((ts_start, ts_end, ttype, response, rt))
        trial_log = np.array(self.trial_log)

        POKE = trial_log[:,3]=='POKE'
        SPOUT = trial_log[:,3]=='SPOUT'
        RESPONSE = POKE | SPOUT
        NOGO = trial_log[:,2]=='NOGO'
        GO = trial_log[:,2]=='GO'

        self.num_go = (GO).sum()
        self.num_go_response = (GO&RESPONSE).sum()
        self.num_hit = (GO&SPOUT).sum()

        self.response_hit_frac = self.num_hit/self.num_go_response
        self.hit_frac = self.num_hit/self.num_go

        self.num_nogo = (NOGO).sum()
        self.num_nogo_response = (NOGO&RESPONSE).sum()
        self.num_fa = (NOGO&SPOUT).sum()

        self.response_fa_frac = self.num_fa/self.num_nogo_response
        self.fa_frac = self.num_fa/self.num_nogo

PositiveData = PositiveData_0_1

if __name__ == '__main__':
    pass

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
                   ('response', 'S16')]
    #ACTION_DTYPE = [('ts', 'i'), ('action', 'S16')]

    trial_log = List(Tuple(Int, Int, Str, Str), store='table', dtype=TRIAL_DTYPE)
    #action_log = List(Tuple(Int, Str), store='table', dtype=ACTION_DTYPE)

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
        if self.poke_TTL.get_range_index(ts_start, ts_end).all():
            response = 'NO_WITHDRAW'
        elif self.spout_TTL.get_range_index(ts_start, ts_end).any():
            response = 'SPOUT'
        elif self.poke_TTL.get_range_index(ts_end, ts_end+1)[0] == 1:
            response = 'POKE'
        else:
            response = 'NO_RESPONSE'

        self.trial_log.append((ts_start, ts_end, ttype, response))
        self.update_score()

    def update_score(self):
        trial_log = np.array(self.trial_log)

        POKE = trial_log[:,3]=='POKE'
        SPOUT = trial_log[:,3]=='SPOUT'
        RESPONSE = POKE | SPOUT
        NOGO = trial_log[:,2]=='NOGO'
        GO = trial_log[:,2]=='GO'

        self.num_go = (GO).sum()
        self.num_go_response = (GO&RESPONSE).sum()
        self.num_hit = (GO&SPOUT).sum()

        #self.response_hit_frac = (GO&SPOUT).sum()/(GO&RESPONSE).sum()
        self.response_hit_frac = self.num_hit/self.num_go_response
        self.hit_frac = self.num_hit/self.num_go

        self.num_nogo = (NOGO).sum()
        self.num_nogo_response = (NOGO&RESPONSE).sum()
        self.num_fa = (NOGO&SPOUT).sum()

        self.response_fa_frac = self.num_fa/self.num_nogo_response
        self.fa_frac = self.num_fa/self.num_nogo

    #def _score_trial(self, ts, type):
    #    pass

    #def _generate_action_log(self):
    #    ts = lambda TTL: np.flatnonzero(TTL)
    #    edge_rising = lambda TTL: np.r_[0, np.diff(TTL.astype('i'))] == 1
    #    edge_falling = lambda TTL: np.r_[0, np.diff(TTL.astype('i'))] == -1

    #    spout_TTL = self.spout_TTL.buffer[:]
    #    poke_TTL = self.poke_TTL.buffer[:]
    #    trial_TTL = self.trial_TTL.buffer[:]
    #    score_TTL = self.score_TTL.buffer[:]
    #    response_TTL = self.response_TTL.buffer[:]

    #    # Spout contact when there's no trial
    #    TTL = edge_rising(spout_TTL) & ~score_TTL
    #    nontrial_spout_ts = ts(TTL).tolist()

    #    # Poke-withdraw when there's no trial
    #    TTL = edge_falling(poke_TTL) & ~response_TTL
    #    nontrial_poke_wd_ts = ts(TTL).tolist()

    #    # Repoke during response window
    #    TTL = edge_rising(poke_TTL) & score_TTL
    #    trial_poke_ts = ts(TTL).tolist()

    #    # Spout contact during response window
    #    TTL = edge_rising(spout_TTL) & score_TTL
    #    trial_spout_ts = ts(TTL).tolist()

    #    actions = ('nontrial_spout',
    #               'nontrial_poke_wd',
    #               'trial_poke',
    #               'trial_spout'
    #               )

    #    self.action_log = []
    #    for action in actions:
    #        timestamps = locals()[action+'_ts']#[getattr(self, action+'_ts')
    #        action = action.upper()
    #        data = [(ts, action) for ts in timestamps]
    #        self.action_log.extend(data)
    #    self.action_log.sort(reverse=True)

PositiveData = PositiveData_0_1

class Test():

    spout_TTL = ['00000000000000111100000000000111100000000000']
    trial_TTL = ['00000000000000000000011111111111100000000000']
    poke_TTL  = ['00000000000000000001111110000000000000000000']

if __name__ == '__main__':
    pass

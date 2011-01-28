from __future__ import division

from abstract_experiment_data import AbstractExperimentData
from sdt_data_mixin import SDTDataMixin
from cns.channel import FileChannel
from enthought.traits.api import Instance, List, CFloat, Int, Float, Any, \
    Range, DelegatesTo, cached_property, on_trait_change, Array, Event, \
    Property, Undefined, Callable, Str, Enum, Bool, Int, Str, Tuple
from datetime import datetime
import numpy as np
from cns.data.h5_utils import append_node, get_or_append_node
from cns.pipeline import deinterleave, broadcast

from cns.channel import Timeseries


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

class PositiveData_0_1(AbstractExperimentData, SDTDataMixin):

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
    response_TTL = Instance(FileChannel, 
            store='channel', store_path='contact/response_TTL')
    pump_TTL = Instance(FileChannel,
            store='channel', store_path='contact/pump_TTL')
    signal_TTL = Instance(FileChannel,
            store='channel', store_path='contact/signal_TTL')
    reaction_TTL = Instance(FileChannel,
            store='channel', store_path='contact/reaction_TTL')
    reward_TTL = Instance(FileChannel,
            store='channel', store_path='contact/reward_TTL')

    trial_start_timestamp = Instance('cns.channel.Timeseries', ())
    trial_end_timestamp = Instance('cns.channel.Timeseries', ())
    timeout_start_timestamp = Instance('cns.channel.Timeseries', ())
    timeout_end_timestamp = Instance('cns.channel.Timeseries', ())

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

    def _reaction_TTL_default(self):
        return self._create_channel('reaction_TTL', np.bool)

    def _pump_TTL_default(self):
        return self._create_channel('pump_TTL', np.bool)

    def _signal_TTL_default(self):
        return self._create_channel('signal_TTL', np.bool)

    def _response_TTL_default(self):
        return self._create_channel('response_TTL', np.bool)

    def _reward_TTL_default(self):
        return self._create_channel('reward_TTL', np.bool)

    TRIAL_DTYPE = [('parameter', 'f'), ('ts_start', 'i'), ('ts_end', 'i'),
                   ('type', 'S4'), ('response', 'S16'), ('reaction_time', 'f')]

    trial_log = List(Tuple(Float, Int, Int, Str, Str, Float), store='table',
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

    def log_trial(self, ts_start, ts_end, ttype, parameter):
        log.debug('Logging trial %s (%d, %d)', ttype, ts_start, ts_end)

        ts_start = int(ts_start)
        ts_end = int(ts_end)

        poke_data = self.poke_TTL.get_range_index(ts_start, ts_end)
        spout_data = self.spout_TTL.get_range_index(ts_start, ts_end)
        if poke_data.all():
            response = 'no withdraw'
        elif spout_data.any():
            response = 'spout'
        elif poke_data[-1] == 1:
            response = 'poke'
        else:
            response = 'no response'

        try:
            if response == 'spout':
                reaction_time = ts(edge_rising(spout_data))[0]/self.spout_TTL.fs
            elif response == 'poke':
                reaction_time = ts(edge_rising(poke_data))[0]/self.poke_TTL.fs
            else:
                reaction_time = -1
        except:
            reaction_time = -1
            
        data = parameter, ts_start, ts_end, ttype, response, reaction_time
        self.trial_log.append(data)
        log.debug("Finished analyzing trial")

    ts_seq = Property(Array('i'), depends_on='trial_log')
    par_seq = Property(Array('f'), depends_on='trial_log')
    ttype_seq = Property(Array('S'), depends_on='trial_log')
    resp_seq = Property(Array('S'), depends_on='trial_log')

    go_indices = Property(Array('i'), depends_on='ttype_seq')
    nogo_indices = Property(Array('i'), depends_on='ttype_seq')

    par_go_mask = Property(List(Array('b')), depends_on='trial_log')
    par_nogo_mask = Property(List(Array('b')), depends_on='trial_log')
    par_spout_mask = Property(List(Array('b')), depends_on='trial_log')
    par_poke_mask = Property(List(Array('b')), depends_on='trial_log')

    par_go_count = Property(List(Int), depends_on='trial_log')
    par_nogo_count = Property(List(Int), depends_on='trial_log')
    par_hit_count = Property(List(Int), depends_on='trial_log')
    par_fa_count = Property(List(Int), depends_on='trial_log')

    par_hit_frac = Property(List(Float), depends_on='trial_log')
    par_fa_frac = Property(List(Float), depends_on='trial_log')

    pars = Property(List(Int), depends_on='trial_log')
    go_trial_count = Property(Int, store='attribute', depends_on='trial_log')

    @cached_property
    def _get_ts_seq(self):
        return [t[1] for t in self.trial_log]

    @cached_property
    def _get_par_seq(self):
        return [t[0] for t in self.trial_log]

    @cached_property
    def _get_ttype_seq(self):
        return [t[3] for t in self.trial_log]

    @cached_property
    def _get_resp_seq(self):
        return [t[4] for t in self.trial_log]

    def _get_indices(self, ttype):
        if len(self.ttype_seq):
            mask = np.asarray(self.ttype_seq)==ttype
            return np.flatnonzero(mask)
        else:
            return []

    @cached_property
    def _get_go_indices(self):
        return self._get_indices('GO')

    @cached_property
    def _get_nogo_indices(self):
        return self._get_indices('NOGO')

    def _get_par_mask(self, sequence, value):
        log.debug("Getting par mask")
        mask = np.array(sequence) == value
        return [np.equal(self.par_seq, par) & mask for par in self.pars]

    @cached_property
    def _get_par_nogo_mask(self):
        return self._get_par_mask(self.ttype_seq, 'NOGO')

    @cached_property
    def _get_par_go_mask(self):
        return self._get_par_mask(self.ttype_seq, 'GO')

    @cached_property
    def _get_par_spout_mask(self):
        return self._get_par_mask(self.resp_seq, 'spout')

    @cached_property
    def _get_par_poke_mask(self):
        return self._get_par_mask(self.resp_seq, 'poke')

    @cached_property
    def _get_par_go_count(self):
        return apply_mask(len, self.par_seq, self.par_go_mask)

    @cached_property
    def _get_par_nogo_count(self):
        return apply_mask(len, self.par_seq, self.par_nogo_mask)

    @cached_property
    def _get_par_hit_count(self):
        mask = [go & spout for go, spout in \
                zip(self.par_go_mask, self.par_spout_mask)]
        return apply_mask(len, self.par_seq, mask)

    @cached_property
    def _get_par_fa_count(self):
        mask = [nogo & spout for nogo, spout in \
                zip(self.par_nogo_mask, self.par_spout_mask)]
        return apply_mask(len, self.par_seq, mask)

    @cached_property
    def _get_pars(self):
        # We only want to return pars for complete trials (e.g. ones for which a
        # go was presented).
        return np.unique(np.take(self.par_seq, self.go_indices, axis=0))

    @cached_property
    def _get_par_hit_frac(self):
        return np.true_divide(self.par_hit_count, self.par_go_count)

    @cached_property
    def _get_par_fa_frac(self):
        return np.true_divide(self.par_fa_count, self.par_nogo_count)

    @cached_property
    def _get_go_trial_count(self):
        return len(self.go_indices)

PositiveData = PositiveData_0_1

if __name__ == '__main__':
    pass
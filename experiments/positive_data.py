from __future__ import division

from scipy import stats
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


from enthought.chaco.api import AbstractPlotData

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

# Version log
#
# V2.0 - 110315 - Fixed bug in par_info where fa_frac and hit_frac columns were
# swapped.  Script migrate_positive_data_v1_v2 will correct this bug.
# V2.1 - 110330 - Added TO_TTL and TO_safe_TTL
# V2.2 - 110330 - Renamed reaction_time to response_time and added the *actual*
# reaction_time.  Response time now reflects the time from trial onset to the
# the time the subject touches the spout or the nose-poke (note that in V2.1 and
# earlier, this is reflected by the value in the (mis-named) reaction_time
# column.  If response time is NaN, that means there was no response. Reaction
# time is the time from signal onset to nose-poke withdraw.  If reaction time is
# NaN, that means there was no withdraw from the nose-poke.
class PositiveData_0_1(AbstractExperimentData, SDTDataMixin, AbstractPlotData):

    # VERSION is a reserved keyword in HDF5 files, so I avoid using it here.
    OBJECT_VERSION = Float(2.2, store='attribute')

    def get_data(self, name):
        return getattr(self, name)

    store_node = Any

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
    TO_TTL = Instance(FileChannel,
            store='channel', store_path='contact/TO_TTL')
    TO_safe_TTL = Instance(FileChannel,
            store='channel', store_path='contact/TO_safe_TTL')

    trial_start_timestamp = Instance('cns.channel.Timeseries', ())
    trial_end_timestamp = Instance('cns.channel.Timeseries', ())
    timeout_start_timestamp = Instance('cns.channel.Timeseries', ())
    timeout_end_timestamp = Instance('cns.channel.Timeseries', ())

    def _create_channel(self, name, dtype):
        contact_node = get_or_append_node(self.store_node, 'contact')
        return FileChannel(node=contact_node, name=name, dtype=dtype)

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

    def _TO_TTL_default(self):
        return self._create_channel('TO_TTL', np.bool)

    def _TO_safe_TTL_default(self):
        return self._create_channel('TO_safe_TTL', np.bool)

    TRIAL_DTYPE = [('parameter', 'f'), ('ts_start', 'i'), ('ts_end', 'i'),
                   ('type', 'S4'), ('response', 'S16'), ('response_time', 'f'),
                   ('reaction_time', 'f')]

    trial_log = List(store='table', dtype=TRIAL_DTYPE)

    mean_reaction_time = Property(store='attribute', depends_on='trial_log')
    mean_response_time = Property(store='attribute', depends_on='trial_log')
    mean_react_to_resp_time = Property(store='attribute', depends_on='trial_log')
    median_reaction_time = Property(store='attribute', depends_on='trial_log')
    median_response_time = Property(store='attribute', depends_on='trial_log')
    #median_react_to_resp_time = Property(store='attribute', depends_on='trial_log')
    var_reaction_time = Property(store='attribute', depends_on='trial_log')
    var_response_time = Property(store='attribute', depends_on='trial_log')
    var_react_to_resp_time = Property(store='attribute', depends_on='trial_log')

    def _get_mean_reaction_time(self):
        return stats.nanmean(self.react_time_seq)

    def _get_mean_response_time(self):
        return stats.nanmean(self.resp_time_seq)

    def _get_mean_react_to_resp_time(self):
        return self.mean_response_time-self.mean_reaction_time

    def _get_median_reaction_time(self):
        return stats.nanmedian(self.react_time_seq)

    def _get_median_response_time(self):
        return stats.nanmedian(self.resp_time_seq)

    def _get_var_reaction_time(self):
        return stats.nanstd(self.react_time_seq)**2

    def _get_var_response_time(self):
        return stats.nanstd(self.resp_time_seq)**2

    def _get_var_react_to_resp_time(self):
        return self.var_reaction_time+self.var_response_time

    def log_trial(self, ts_start, ts_end, ttype, parameter):
        resp, resp_time, react_time = self.compute_response(ts_start, ts_end)
        data = parameter, ts_start, ts_end, ttype, resp, resp_time, react_time
        self.trial_log.append(data)

    def compute_response(self, ts_start, ts_end):
        '''
        Response array
        --------------
        * spout
        * poke
        * no withdraw
        * no response

        Early response array (boolean)
        Trial type array (GO | NOGO)

        Default method for computing scores
        HIT - go & spout & !early
        MISS - go & (poke | no_response) & !early

        FA - (nogo & spout) | (early & spout)
        CR - (nogo | early) & !spout
        '''
        ts_start = int(ts_start)
        ts_end = int(ts_end)
        poke_data = self.poke_TTL.get_range_index(ts_start, ts_end)
        spout_data = self.spout_TTL.get_range_index(ts_start, ts_end)
        react_data = self.reaction_TTL.get_range_index(ts_start, ts_end)
        if not react_data.any():
            response = 'early withdraw'
        elif poke_data.all():
            response = 'no withdraw'
        elif spout_data.any():
            response = 'spout'
        elif poke_data[-1] == 1:
            response = 'poke'
        else:
            response = 'no response'

        try:
            if response == 'spout':
                response_time = ts(edge_rising(spout_data))[0]/self.spout_TTL.fs
            elif response == 'poke':
                response_time = ts(edge_rising(poke_data))[0]/self.poke_TTL.fs
            else:
                response_time = np.nan
        except:
            response_time = np.nan

        try:
            reaction_time = ts(edge_falling(poke_data))[0]/self.poke_TTL.fs
        except:
            reaction_time = np.nan

        return response, response_time, reaction_time

    # timestamp sequence
    ts_seq          = Property(Array('i'), depends_on='trial_log')
    # parameter sequence
    par_seq         = Property(Array('f'), depends_on='trial_log')
    # trial type sequence (GO or NOGO)
    ttype_seq       = Property(Array('S'), depends_on='trial_log')
    # response (e.g. no response, early withdraw, etc) sequence
    resp_seq        = Property(Array('S'), depends_on='trial_log')
    # response time sequence
    resp_time_seq   = Property(Array('f'), depends_on='trial_log')
    # reaction time sequence
    react_time_seq  = Property(Array('f'), depends_on='trial_log')

    go_indices   = Property(Array('i'), depends_on='ttype_seq')
    nogo_indices = Property(Array('i'), depends_on='ttype_seq')

    par_go_mask = Property(List(Array('b')), depends_on='trial_log')
    par_nogo_mask = Property(List(Array('b')), depends_on='trial_log')
    par_spout_mask = Property(List(Array('b')), depends_on='trial_log')
    par_poke_mask = Property(List(Array('b')), depends_on='trial_log')
    par_no_response_mask = Property(List(Array('b')), depends_on='trial_log')
    par_no_withdraw_mask = Property(List(Array('b')), depends_on='trial_log')

    par_go_count = Property(List(Int), depends_on='trial_log')
    par_nogo_count = Property(List(Int), depends_on='trial_log')
    par_hit_count = Property(List(Int), depends_on='trial_log')
    par_fa_count = Property(List(Int), depends_on='trial_log')

    par_hit_frac = Property(List(Float), depends_on='trial_log')
    par_fa_frac = Property(List(Float), depends_on='trial_log')
    
    global_fa_frac = Property(Float, depends_on='trial_log')

    pars = Property(List(Int), depends_on='trial_log')
    go_trial_count = Property(Int, store='attribute', depends_on='trial_log')
    nogo_trial_count = Property(Int, store='attribute', depends_on='trial_log')

    PAR_INFO_DTYPE = [
            ('par', 'f'), 
            ('nogo_count', 'i'),
            ('go_count', 'i'),
            ('fa_count', 'i'),
            ('hit_count', 'i'),
            ('hit_frac', 'f'),
            ('fa_frac', 'f'),
            ('d', 'f'),
            ]
    par_info = Property(store='table', dtype=PAR_INFO_DTYPE)

    def _get_par_info(self):
        return zip(self.pars, self.par_nogo_count, self.par_go_count,
                self.par_fa_count, self.par_hit_count, self.par_fa_frac,
                self.par_hit_frac, self.par_dprime)

    @cached_property
    def _get_par_seq(self):
        return [t[0] for t in self.trial_log]

    @cached_property
    def _get_ts_seq(self):
        return [t[1] for t in self.trial_log]

    @cached_property
    def _get_ttype_seq(self):
        return [t[3] for t in self.trial_log]

    @cached_property
    def _get_resp_seq(self):
        return [t[4] for t in self.trial_log]

    @cached_property
    def _get_resp_time_seq(self):
        return [t[5] for t in self.trial_log]

    @cached_property
    def _get_react_time_seq(self):
        return [t[6] for t in self.trial_log]

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
        value_mask = np.array(sequence) == value
        result = []
        for par in self.pars:
            par_mask = np.equal(self.par_seq, par)
            if par_mask.ndim != 1:
                par_mask = par_mask.all(axis=-1)
            result.append(par_mask & value_mask)
        return result

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
        # go_mask is an array of boolean that indicates whether each trial was a
        # go or not.  spout_mask is an array of boolean indicating whether the
        # gerbil went to the spout for that trial.  
        mask = [go & spout for go, spout in \
                zip(self.par_go_mask, self.par_spout_mask)]

        # This is the equivalent of the above line
        #pairs= zip(self.par_go_mask, self.par_spout_mask)
        #mask = []
        #for pair in pairs:
        #    go, spout = pair
        #    hit = go & spout
        #    mask.append(hit)
        return apply_mask(len, self.par_seq, mask)

    @cached_property
    def _get_par_fa_count(self):
        mask = [nogo & spout for nogo, spout in \
                zip(self.par_nogo_mask, self.par_spout_mask)]
        return apply_mask(len, self.par_seq, mask)

    @cached_property
    def _get_par_miss_count(self):
        mask = [go & (poke | no_withdraw) for go, poke, no_withdraw in \
                zip(self.par_go_mask, self.par_poke_mask,
                    self.par_no_withdraw_mask)]

    @cached_property
    def _get_pars(self):
        # We only want to return pars for complete trials (e.g. ones for which a
        # go was presented).
        seq = np.take(self.par_seq, self.go_indices, axis=0)

        try:
            # This should work for "complex" parameters where we are varying the
            # signal across more than one dimension.
            unique = set([tuple(i) for i in seq])
        except:
            unique = set(seq)
        return sorted(unique)

    # Get hit fraction for each parameter
    @cached_property
    def _get_par_hit_frac(self):
        return np.true_divide(self.par_hit_count, self.par_go_count)

    @cached_property
    def _get_par_fa_frac(self):
        return np.true_divide(self.par_fa_count, self.par_nogo_count)

    @cached_property
    def _get_global_fa_frac(self):
        nogo_count = len(self.nogo_indices)

        if nogo_count == 0:
            return np.nan

        nogo_resp = np.take(self.resp_seq, self.nogo_indices)
        # fa_mask is a boolean array where 1 indicates the subject went to the
        # spout.  We can simply compute the sum of this array to determien how
        # many times the subject went to the spout (e.g. "false alarmed")
        fa_mask = nogo_resp == 'spout'
        fa_count = np.sum(fa_mask)

        return float(fa_count)/float(nogo_count)

    @cached_property
    def _get_go_trial_count(self):
        return len(self.go_indices)

    @cached_property
    def _get_nogo_trial_count(self):
        return len(self.nogo_indices)

    @on_trait_change('par_dprime')
    def fire_data_changed(self):
        self.data_changed = True

PositiveData = PositiveData_0_1

if __name__ == '__main__':
    pass

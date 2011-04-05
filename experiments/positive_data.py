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

def apply_mask(fun, masks, values):
    return np.array([fun(values[m]) for m in masks])

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
# V2.3 - 110404 - Revamped trial_log to include an arbitrary dataset.  First
# call to log_trial establishes the columns that will be available.  Subsequent
# calls to log_trial must contain the *exact* same data.  I no longer guarantee
# the column order of the trial_log table.  You will have to explicitly
# query the columns to get the information you need out of the table rather than
# relying on a pre-specified index.
class PositiveData_0_1(AbstractExperimentData, SDTDataMixin, AbstractPlotData):
    '''
    trial_log is essentially a list of the trials, along with the parameters
    and some basic analysis.
    '''

    # VERSION is a reserved keyword in HDF5 files, so I avoid using it here.
    OBJECT_VERSION = Float(2.3, store='attribute')

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

    _trial_log = List
    trial_log = Property(store='table', depends_on='_trial_log')
    trial_log_columns = Tuple()

    @cached_property
    def _get_trial_log(self):
        if len(self._trial_log) > 0:
            return np.rec.fromrecords(self._trial_log,
                    names=self.trial_log_columns)
        else:
            return []

    def log_trial(self, **kwargs):
        ts_start = kwargs['ts_start']
        ts_end = kwargs['ts_end']
        kwargs.update(self.compute_response(ts_start, ts_end))
        kwargs['start'] = ts_start/self.poke_TTL.fs
        kwargs['end'] = ts_end/self.poke_TTL.fs

        # Extract sorted list of values and keys from the dictionary that is to
        # be added to trial_log
        names, record = zip(*sorted(kwargs.items()))
        if len(self.trial_log) == 0:
            self.trial_log_columns = names
            self._trial_log = [record]
        elif names == self.trial_log_columns:
            self._trial_log.append(record)
        else:
            raise ValueError, "Invalid log_trial attempt"

    def compute_response(self, ts_start, ts_end):
        '''
        Available sequences
        -------------------
        Response type   {spout, poke, no withdraw, no response}
        Early response  {True, False}
        Trial type      {GO, NOGO}

        Default method for computing scores
        -----------------------------------
        HIT
            go & spout & ~early
        MISS
            go & (poke | no_response) & ~early
        FA
            (nogo & spout) | (early & spout)
        CR
            (nogo | early) & ~spout
        '''
        poke_data = self.poke_TTL.get_range_index(ts_start, ts_end)
        spout_data = self.spout_TTL.get_range_index(ts_start, ts_end)
        react_data = self.reaction_TTL.get_range_index(ts_start, ts_end)

        # Did subject withdraw from nose-poke before he was allowed to react?
        early = ~react_data.any()

        # Regardless of whether or not the subject reacted early, what was his
        # answer?
        if poke_data.all():
            response = 'no withdraw'
        elif spout_data.any():
            response = 'spout'
        elif poke_data[-1] == 1:
            response = 'poke'
        else:
            response = 'no response'

        # How quickly did he react?
        try:
            reaction_time = ts(edge_falling(poke_data))[0]/self.poke_TTL.fs
        except:
            reaction_time = np.nan

        # How quickly did he provide his answer?
        try:
            if response == 'spout':
                response_time = ts(edge_rising(spout_data))[0]/self.spout_TTL.fs
            elif response == 'poke':
                response_time = ts(edge_rising(poke_data))[0]/self.poke_TTL.fs
            else:
                response_time = np.nan
        except:
            response_time = np.nan

        return dict(early_response=early, response=response,
                response_time=response_time, reaction_time=reaction_time)

    go_indices   = Property(Array('i'), depends_on='ttype_seq')
    nogo_indices = Property(Array('i'), depends_on='ttype_seq')

    pars = Property(List(Int), depends_on='trial_log')
    go_trial_count = Property(Int, store='attribute', depends_on='trial_log')
    nogo_trial_count = Property(Int, store='attribute', depends_on='trial_log')

    par_info = Property(store='table', depends_on='par_dprime')

    parameters = 'attenuation', 'duration'

    @cached_property
    def _get_par_info(self):
        data = {
                #'par':          self.pars,
                'hit_frac':     self.par_hit_frac,
                'fa_frac':      self.par_fa_frac,
                'd':            self.par_dprime,
                'go':           self.par_go_count,
                'nogo':         self.par_nogo_count,
                'hit':          self.par_hit_count,
                'miss':         self.par_miss_count,
                'fa':           self.par_fa_count,
                'cr':           self.par_cr_count,
                'mean_react':   self.par_mean_reaction_time,
                'mean_resp':    self.par_mean_response_time,
                'std_react':    self.par_std_reaction_time,
                'std_resp':     self.par_std_response_time,
                }
        if len(self.pars) != 0:
            for i, par in enumerate(self.parameters):
                data[par] = np.array(self.pars)[..., i]
        return np.rec.fromarrays(data.values(), names=data.keys())

    # Splits trial_log into individual elements as needed
    ts_seq          = Property(Array('i'), depends_on='trial_log')
    par_seq         = Property(Array('f'), depends_on='trial_log')
    ttype_seq       = Property(Array('S'), depends_on='trial_log')
    resp_seq        = Property(Array('S'), depends_on='trial_log')
    resp_time_seq   = Property(Array('f'), depends_on='trial_log')
    react_time_seq  = Property(Array('f'), depends_on='trial_log')
    early_seq       = Property(Array('bool'), depends_on='trial_log')

    @cached_property
    def _get_par_seq(self):
        try:
            return np.array(zip(self.trial_log['duration'],
                       self.trial_log['attenuation']))
        except:
            return np.array([])

    @cached_property
    def _get_ts_seq(self):
        try:
            return self.trial_log['ts_start']
        except:
            return np.array([])

    @cached_property
    def _get_ttype_seq(self):
        try:
            return self.trial_log['ttype']
        except:
            return np.array([])
            return []

    @cached_property
    def _get_resp_seq(self):
        try:
            return self.trial_log['response']
        except:
            return np.array([])
            return []

    @cached_property
    def _get_resp_time_seq(self):
        try:
            return self.trial_log['response_time']
        except:
            return np.array([])
            return []

    @cached_property
    def _get_react_time_seq(self):
        try:
            return self.trial_log['reaction_time']
        except:
            return np.array([])
            return []

    @cached_property
    def _get_early_seq(self):
        try:
            return self.trial_log['early_response']
        except:
            return np.array([])
            return []

    # Sequences of boolean indicating trial type and subject's response.

    go_seq = Property(List(Array('b')), depends_on='trial_log')
    nogo_seq = Property(List(Array('b')), depends_on='trial_log')
    spout_seq = Property(List(Array('b')), depends_on='trial_log')
    poke_seq = Property(List(Array('b')), depends_on='trial_log')
    no_resp_seq = Property(List(Array('b')), depends_on='trial_log')
    no_withdraw_seq = Property(List(Array('b')), depends_on='trial_log')

    @cached_property
    def _get_go_seq(self):
        return self.ttype_seq == 'GO'

    @cached_property
    def _get_nogo_seq(self):
        return self.ttype_seq == 'NOGO'

    @cached_property
    def _get_poke_seq(self):
        return self.resp_seq == 'poke'

    @cached_property
    def _get_spout_seq(self):
        return self.resp_seq == 'spout'

    @cached_property
    def _get_no_withdraw_seq(self):
        return self.resp_seq == 'no withdraw'

    @cached_property
    def _get_no_resp_seq(self):
        return self.resp_seq == 'no response'

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

    #def _get_par_mask(self, sequence, value):
    #    value_mask = np.array(sequence) == value
    #    result = []
    #    for par in self.pars:
    #        par_mask = np.equal(self.par_seq, par)
    #        if par_mask.ndim != 1:
    #            par_mask = par_mask.all(axis=-1)
    #        result.append(par_mask & value_mask)
    #    return result

    par_mask = Property(depends_on='trial_log')

    @cached_property
    def _get_par_mask(self):
        result = []
        for par in self.pars:
            #m = np.equal(self.par_seq, par)
            m = self.par_seq == par
            if m.ndim != 1:
                m = m.all(axis=-1)
            result.append(m)
        return result

    par_go_mask = Property(depends_on='par_mask')

    @cached_property
    def _get_par_go_mask(self):
        return [self.go_seq & m for m in self.par_mask]

    #@cached_property
    #def _get_par_nogo_mask(self):
    #    return self._get_par_mask(self.ttype_seq, 'NOGO')

    #@cached_property
    #def _get_par_go_mask(self):
    #    return self._get_par_mask(self.ttype_seq, 'GO')

    #@cached_property
    #def _get_par_spout_mask(self):
    #    return self._get_par_mask(self.resp_seq, 'spout')

    #@cached_property
    #def _get_par_poke_mask(self):
    #    return self._get_par_mask(self.resp_seq, 'poke')

    #@cached_property
    #def _get_par_go_count(self):
    #    return apply_mask(len, self.par_seq, self.par_go_mask)

    #@cached_property
    #def _get_par_nogo_count(self):
    #    return apply_mask(len, self.par_seq, self.par_nogo_mask)


    # MY NEW STUFF
    par_go_count = Property(depends_on='go_seq')
    par_nogo_count = Property(depends_on='nogo_seq')

    @cached_property
    def _get_par_go_count(self):
        return apply_mask(np.sum, self.par_mask, self.go_seq)

    @cached_property
    def _get_par_nogo_count(self):
        return apply_mask(np.sum, self.par_mask, self.nogo_seq)

    hit_seq = Property(depends_on='trial_log')
    par_hit_count = Property(depends_on='hit_seq')
    miss_seq = Property(depends_on='trial_log')
    par_miss_count = Property(depends_on='miss_seq')
    fa_seq = Property(depends_on='trial_log')
    par_fa_count = Property(depends_on='fa_seq')
    cr_seq = Property(depends_on='trial_log')
    par_cr_count = Property(depends_on='cr_seq')

    @cached_property
    def _get_hit_seq(self):
        return self.go_seq & self.spout_seq & ~self.early_seq

    @cached_property
    def _get_par_hit_count(self):
        return apply_mask(np.sum, self.par_mask, self.hit_seq)

    @cached_property
    def _get_miss_seq(self):
        return self.go_seq & (self.poke_seq | self.no_resp_seq) & \
                ~self.early_seq

    @cached_property
    def _get_par_miss_count(self):
        return apply_mask(np.sum, self.par_mask, self.miss_seq)

    @cached_property
    def _get_fa_seq(self):
        return (self.nogo_seq & self.spout_seq) | \
               (self.early_seq & self.spout_seq)

    @cached_property
    def _get_par_fa_count(self):
        return apply_mask(np.sum, self.par_mask, self.fa_seq)

    @cached_property
    def _get_cr_seq(self):
        return (self.nogo_seq | self.early_seq) & ~self.spout_seq

    @cached_property
    def _get_par_cr_count(self):
        return apply_mask(np.sum, self.par_mask, self.cr_seq)

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

    par_hit_frac = Property(List(Float), 
            depends_on='par_hit_count, par_miss_count')
    par_fa_frac = Property(List(Float), 
            depends_on='par_cr_count, par_fa_count')
    global_fa_frac = Property(Float, depends_on='trial_log')

    @cached_property
    def _get_par_hit_frac(self):
        return self.par_hit_count/(self.par_hit_count+self.par_miss_count)

    @cached_property
    def _get_par_fa_frac(self):
        return self.par_fa_count/(self.par_fa_count+self.par_cr_count)

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
        return np.sum(self.go_seq)

    @cached_property
    def _get_nogo_trial_count(self):
        return np.sum(self.nogo_seq)

    @on_trait_change('par_dprime')
    def fire_data_changed(self):
        self.data_changed = True

    par_mean_reaction_time = Property(depends_on='react_time_seq')
    par_mean_response_time = Property(depends_on='resp_time_seq')
    #par_mean_react_to_resp_time = Property(depends_on='trial_log')
    #par_median_reaction_time = Property(depends_on='trial_log')
    #par_median_response_time = Property(depends_on='trial_log')
    par_std_reaction_time = Property(depends_on='react_time_seq')
    par_std_response_time = Property(depends_on='resp_time_seq')
    #par_var_react_to_resp_time = Property(depends_on='trial_log')

    def _get_par_mean_reaction_time(self):
        return apply_mask(stats.nanmean, self.par_go_mask, self.react_time_seq)

    def _get_par_mean_response_time(self):
        return apply_mask(stats.nanmean, self.par_go_mask, self.resp_time_seq)

    def _get_par_std_reaction_time(self):
        return apply_mask(stats.nanstd, self.par_go_mask, self.react_time_seq)

    def _get_par_std_response_time(self):
        return apply_mask(stats.nanstd, self.par_go_mask, self.resp_time_seq)

    #def _get_par_mean_reaction_time(self):
    #    return stats.nanmean(self.react_time_seq)

    #def _get_mean_response_time(self):
    #    return stats.nanmean(self.resp_time_seq)

    #def _get_mean_react_to_resp_time(self):
    #    return self.mean_response_time-self.mean_reaction_time

    #def _get_median_reaction_time(self):
    #    return stats.nanmedian(self.react_time_seq)

    #def _get_median_response_time(self):
    #    return stats.nanmedian(self.resp_time_seq)

    #def _get_var_reaction_time(self):
    #    return stats.nanstd(self.react_time_seq)**2

    #def _get_var_response_time(self):
    #    return stats.nanstd(self.resp_time_seq)**2

    #def _get_var_react_to_resp_time(self):
    #    return self.var_reaction_time+self.var_response_time


PositiveData = PositiveData_0_1

if __name__ == '__main__':
    pass

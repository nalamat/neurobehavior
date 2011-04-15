from __future__ import division

from scipy import stats
from abstract_experiment_data import AbstractExperimentData
from sdt_data_mixin import SDTDataMixin
from cns.channel import FileChannel
from enthought.traits.api import Instance, List, CFloat, Int, Float, Any, \
    Range, DelegatesTo, cached_property, on_trait_change, Array, Event, \
    Property, Undefined, Callable, Str, Enum, Bool, Int, Str, Tuple, CList
from enthought.traits.ui.api import SetEditor
from datetime import datetime
import numpy as np
from cns.data.h5_utils import append_node, get_or_append_node
from cns.pipeline import deinterleave, broadcast

from cns.channel import Timeseries


from enthought.traits.ui.api import CheckListEditor
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
# V2.4 - 110415 - Switch to a volume-based reward made detection of gerbil on
# spout slightly problematic.  Made scoring more robust.  pump_TTL data is now
# being spooled again; however, this is simply an indicator of whether a trigger
# was sent to the pump rather than an indicator of how long the pump was running
# for.
class PositiveData_0_1(AbstractExperimentData, SDTDataMixin, AbstractPlotData):
    '''
    trial_log is essentially a list of the trials, along with the parameters
    and some basic analysis.
    '''

    def get_data(self, name):
        return getattr(self, name)

    # VERSION is a reserved keyword in HDF5 files, so I avoid using it here.
    OBJECT_VERSION = Float(2.4, store='attribute')

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

    #trial_start_timestamp   = Instance('cns.channel.Timeseries', ())
    #trial_end_timestamp     = Instance('cns.channel.Timeseries', ())
    #timeout_start_timestamp = Instance('cns.channel.Timeseries', ())
    #timeout_end_timestamp   = Instance('cns.channel.Timeseries', ())

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

    def log_trial(self, score=True, **kwargs):
        # Typically we want score to be True; however, for debugging purposes it
        # is convenient to set score to False that way we don't need to provide
        # the "dummy" spout and poke data required for scoring.
        if score:
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

        # Did subject withdraw from nose-poke before or after he was allowed to
        # react?
        if ~react_data.any():
            reaction = 'early'
        elif poke_data[react_data].all():
            reaction = 'late'
        else:
            reaction = 'normal'

        # Regardless of whether or not the subject reacted early, what was his
        # response?
        if spout_data.any():
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

        return dict(reaction=reaction, response=response,
                response_time=response_time, reaction_time=reaction_time)

    go_indices   = Property(Array('i'), depends_on='ttype_seq')
    nogo_indices = Property(Array('i'), depends_on='ttype_seq')

    pars = Property(List(Int), depends_on='trial_log')
    go_trial_count = Property(Int, store='attribute', depends_on='trial_log')
    nogo_trial_count = Property(Int, store='attribute', depends_on='trial_log')

    par_info = Property(store='table', depends_on='par_dprime')

    parameters = List(editor=SetEditor(name='trial_log_columns',
                                       can_move_all=False,
                                       ordered=True))

    @cached_property
    def _get_par_info(self):
        data = {
                'parameter':     [repr(p).strip(',()') for p in self.pars],
                'hit_frac':      self.par_hit_frac,
                'fa_frac':       self.par_fa_frac,
                'd':             self.par_dprime,
                'criterion':     self.par_criterion,
                'go':            self.par_go_count,
                'nogo':          self.par_nogo_count,
                'go_nogo_ratio': self.par_go_nogo_ratio,
                'hit':           self.par_hit_count,
                'miss':          self.par_miss_count,
                'fa':            self.par_fa_count,
                'cr':            self.par_cr_count,
                'mean_react':    self.par_mean_reaction_time,
                'mean_resp':     self.par_mean_response_time,
                'median_react':  self.par_median_response_time,
                'median_resp':   self.par_median_response_time,
                'std_react':     self.par_std_reaction_time,
                'std_resp':      self.par_std_response_time,
                }
        for i, parameter in enumerate(self.parameters):
            data[parameter] = [p[i] for p in self.pars]
        return np.rec.fromarrays(data.values(), names=data.keys())

    # Splits trial_log into individual sequences as needed
    ts_seq          = Property(Array('i'), depends_on='trial_log')
    par_seq         = Property(Array('f'), depends_on='trial_log')
    ttype_seq       = Property(Array('S'), depends_on='trial_log')
    resp_seq        = Property(Array('S'), depends_on='trial_log')
    resp_time_seq   = Property(Array('f'), depends_on='trial_log')
    react_time_seq  = Property(Array('f'), depends_on='trial_log')
    react_seq       = Property(Array('S'), depends_on='trial_log')

    # The following sequences need to handle the edge case where the trial log
    # is initially empty (and has no known record fields to speak of).

    @cached_property
    def _get_par_seq(self):
        try:
            arr = np.empty(len(self.trial_log), dtype=object)
            arr[:] = zip(*[self.trial_log[p] for p in self.parameters])
            return arr
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

    @cached_property
    def _get_resp_seq(self):
        try:
            return self.trial_log['response']
        except:
            return np.array([])

    @cached_property
    def _get_resp_time_seq(self):
        try:
            return self.trial_log['response_time']
        except:
            return np.array([])

    @cached_property
    def _get_react_time_seq(self):
        try:
            return self.trial_log['reaction_time']
        except:
            return np.array([])

    @cached_property
    def _get_react_seq(self):
        try:
            return self.trial_log['reaction']
        except:
            return np.array([])

    # Sequences of boolean indicating trial type and subject's response.

    # Trial type sequences
    go_seq      = Property(Array('b'), depends_on='trial_log')
    nogo_seq    = Property(Array('b'), depends_on='trial_log')

    # Response sequences
    spout_seq   = Property(Array('b'), depends_on='trial_log')
    poke_seq    = Property(Array('b'), depends_on='trial_log')
    nr_seq      = Property(Array('b'), depends_on='trial_log')

    # Reaction sequences
    late_seq    = Property(Array('b'), depends_on='trial_log')
    early_seq   = Property(Array('b'), depends_on='trial_log')
    normal_seq  = Property(Array('b'), depends_on='trial_log')

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
    def _get_nr_seq(self):
        return self.resp_seq == 'no response'

    @cached_property
    def _get_late_seq(self):
        return self.react_seq == 'late'

    @cached_property
    def _get_early_seq(self):
        return self.react_seq == 'early'

    @cached_property
    def _get_normal_seq(self):
        return self.react_seq == 'normal'

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

    par_mask = Property(depends_on='trial_log')

    @cached_property
    def _get_par_mask(self):
        result = []
        # Numpy's equal function casts the argument on either side of the
        # operator to an array.  Numpy's default handling of tuples is to
        # convert it to an array where each element of the tuple is an element
        # in the array.  We need to do the casting ourself (e.g. ensure that we
        # have a single-element array where the element is a tuple).
        cmp_array = np.empty(1, dtype=object)
        for par in self.pars:
            cmp_array[0] = par
            m = self.par_seq == cmp_array
            result.append(m)
        return result

    par_go_mask     = Property(depends_on='trial_log')

    @cached_property
    def _get_par_go_mask(self):
        return [self.go_seq & m for m in self.par_mask]

    # MY NEW STUFF
    par_go_count    = Property(depends_on='trial_log')
    par_nogo_count  = Property(depends_on='trial_log')

    @cached_property
    def _get_par_go_count(self):
        return self.par_hit_count+self.par_miss_count

    @cached_property
    def _get_par_nogo_count(self):
        return self.par_fa_count+self.par_cr_count

    hit_seq         = Property(depends_on='trial_log')
    par_hit_count   = Property(depends_on='trial_log')
    miss_seq        = Property(depends_on='trial_log')
    par_miss_count  = Property(depends_on='trial_log')
    fa_seq          = Property(depends_on='trial_log')
    par_fa_count    = Property(depends_on='trial_log')
    cr_seq          = Property(depends_on='trial_log')
    par_cr_count    = Property(depends_on='trial_log')

    @cached_property
    def _get_hit_seq(self):
        return self.go_seq & self.normal_seq & self.spout_seq

    @cached_property
    def _get_par_hit_count(self):
        return apply_mask(np.sum, self.par_mask, self.hit_seq)

    @cached_property
    def _get_miss_seq(self):
        return self.go_seq & (self.poke_seq | self.nr_seq) & self.normal_seq

    @cached_property
    def _get_par_miss_count(self):
        return apply_mask(np.sum, self.par_mask, self.miss_seq)

    @cached_property
    def _get_fa_seq(self):
        return (self.early_seq & self.spout_seq) | \
               (self.nogo_seq & self.normal_seq & self.spout_seq)

    @cached_property
    def _get_par_fa_count(self):
        return apply_mask(np.sum, self.par_mask, self.fa_seq)

    @cached_property
    def _get_cr_seq(self):
        return ((self.nogo_seq & self.normal_seq) | self.early_seq) & \
                ~self.spout_seq

    @cached_property
    def _get_par_cr_count(self):
        return apply_mask(np.sum, self.par_mask, self.cr_seq)

    @cached_property
    def _get_pars(self):
        # We only want to return pars for complete trials (e.g. ones for which a
        # go was presented).
        return np.unique(self.par_seq)

    par_hit_frac = Property(List(Float), depends_on='trial_log')
    par_fa_frac = Property(List(Float), depends_on='trial_log')
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

    max_reaction_time = Property(depends_on='trial_log', store='attribute')
    max_response_time = Property(depends_on='trial_log', store='attribute')

    @cached_property
    def _get_max_reaction_time(self):
        if len(self.par_mean_reaction_time) == 0:
            return np.nan
        return np.max(self.par_mean_reaction_time)

    @cached_property
    def _get_max_response_time(self):
        if len(self.par_mean_response_time) == 0:
            return np.nan
        return np.max(self.par_mean_response_time)

    @cached_property
    def _get_go_trial_count(self):
        return np.sum(self.go_seq)

    @cached_property
    def _get_nogo_trial_count(self):
        return np.sum(self.nogo_seq)

    @on_trait_change('par_dprime')
    def fire_data_changed(self):
        self.data_changed = True

    par_go_nogo_ratio = Property(depends_on='trial_log')

    @cached_property
    def _get_par_go_nogo_ratio(self):
        return self.par_go_count/self.par_nogo_count

    par_mean_reaction_time      = Property(depends_on='trial_log')
    par_mean_response_time      = Property(depends_on='trial_log')
    par_median_reaction_time    = Property(depends_on='trial_log')
    par_median_response_time    = Property(depends_on='trial_log')
    par_std_reaction_time       = Property(depends_on='trial_log')
    par_std_response_time       = Property(depends_on='trial_log')

    def _get_par_mean_reaction_time(self):
        return apply_mask(stats.nanmean, self.par_go_mask, self.react_time_seq)

    def _get_par_mean_response_time(self):
        return apply_mask(stats.nanmean, self.par_go_mask, self.resp_time_seq)

    def _get_par_median_reaction_time(self):
        return apply_mask(stats.nanmedian, self.par_go_mask, self.react_time_seq)

    def _get_par_median_response_time(self):
        return apply_mask(stats.nanmedian, self.par_go_mask, self.resp_time_seq)

    def _get_par_std_reaction_time(self):
        return apply_mask(stats.nanstd, self.par_go_mask, self.react_time_seq)

    def _get_par_std_response_time(self):
        return apply_mask(stats.nanstd, self.par_go_mask, self.resp_time_seq)

PositiveData = PositiveData_0_1

if __name__ == '__main__':
    pass

from __future__ import division

from scipy import stats
from abstract_experiment_data import AbstractExperimentData
from sdt_data_mixin import SDTDataMixin
from enthought.traits.api import Instance, List, CFloat, Int, Float, Any, \
    Range, DelegatesTo, cached_property, on_trait_change, Array, Event, \
    Property, Undefined, Callable, Str, Enum, Bool, Int, Str, Tuple, CList
from enthought.traits.ui.api import EnumEditor, VGroup, Item, View
from datetime import datetime
import numpy as np
from cns.data.h5_utils import append_node, get_or_append_node
from cns.pipeline import deinterleave, broadcast

from cns.channel import Timeseries, FileChannel

from enthought.traits.ui.api import CheckListEditor
from enthought.chaco.api import AbstractPlotData

import logging
log = logging.getLogger(__name__)

# Score functions
ts = lambda TTL: np.flatnonzero(TTL)
edge_rising = lambda TTL: np.r_[0, np.diff(TTL.astype('i'))] == 1
edge_falling = lambda TTL: np.r_[0, np.diff(TTL.astype('i'))] == -1

def string_array_equal(a, string):
    if len(a) == 0:
        return np.array([])
    else:
        return np.array(a) == string

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
# V2.3 - 110404 - Revamped masked_trial_log to include an arbitrary dataset.  First
# call to log_trial establishes the columns that will be available.  Subsequent
# calls to log_trial must contain the *exact* same data.  I no longer guarantee
# the column order of the masked_trial_log table.  You will have to explicitly
# query the columns to get the information you need out of the table rather than
# relying on a pre-specified index.
# V2.4 - 110415 - Switch to a volume-based reward made detection of gerbil on
# spout slightly problematic.  Made scoring more robust.  pump_TTL data is now
# being spooled again; however, this is simply an indicator of whether a trigger
# was sent to the pump rather than an indicator of how long the pump was running
# for.
# V2.5 - 110418 - Revised global FA fraction computation to be more consistent
# with how we score the actual trials and compute FA for the individual
# parameters.
# V2.6 - 110605 - Added commutator inhibit TTL (comm_inhibit_TTL) to indicate
# when commutator is being suppressed from spinning.
# V2.7 - 110718 - Added microphone data buffer
class PositiveData_0_1(AbstractExperimentData, SDTDataMixin, AbstractPlotData):
    '''
    masked_trial_log is essentially a list of the trials, along with the parameters
    and some basic analysis.
    '''
    mask_mode = Enum('none', 'include recent')
    mask_num = Int(25)
    masked_trial_log = Property(depends_on='mask_+, trial_log')

    def _get_masked_trial_log(self):
        if self.mask_mode == 'none':
            return self.trial_log
        else:
            # Count gos backwards from the end of the array
            if len(self.trial_log) == 0:
                return self.trial_log

            go_seq = string_array_equal(self.trial_log['ttype'], 'GO')
            go_number = go_seq[::-1].cumsum()
            try:
                index = np.nonzero(go_number > self.mask_num)[0][0]
                return self.trial_log[-index:]
            except IndexError:
                return self.trial_log

    c_nogo = Int(0, context=True, immediate=True, label='Consecutive nogos')
    c_hit = Int(0, context=True, immediate=True, label='Consecutive hits')
    c_fa = Int(0, context=True, immediate=True, label='Consecutive false alarms')

    def get_data(self, name):
        return getattr(self, name)

    # VERSION is a reserved keyword in HDF5 files, so I avoid using it here.
    OBJECT_VERSION = Float(2.7, store='attribute')

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
    comm_inhibit_TTL = Instance(FileChannel,
            store='channel', store_path='contact/comm_inhibit_TTL')

    microphone = Instance(FileChannel, store='channel', store_path='microphone')

    def _microphone_default(self):
        return FileChannel(node=self.store_node, name='microphone',
                dtype=np.float32)

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

    def _comm_inhibit_TTL_default(self):
        return self._create_channel('comm_inhibit_TTL', np.bool)

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

        # Log the trial
        AbstractExperimentData.log_trial(self, **kwargs)

        # Now, compute the context data
        self.c_nogo = self.rcount(self.nogo_seq)
        self.c_hit = self.rcount(self.hit_seq[self.go_seq | self.fa_seq])
        self.c_fa = self.rcount(self.fa_seq[self.early_seq | self.nogo_seq])

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
        poke_data = self.poke_TTL.get_range_index(ts_start, ts_end,
                check_bounds=True)
        spout_data = self.spout_TTL.get_range_index(ts_start, ts_end,
                check_bounds=True)
        react_data = self.reaction_TTL.get_range_index(ts_start, ts_end,
                check_bounds=True)

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

    # Splits masked_trial_log into individual sequences as needed
    ts_seq          = Property(Array('i'), depends_on='masked_trial_log')
    ttype_seq       = Property(Array('S'), depends_on='masked_trial_log')
    resp_seq        = Property(Array('S'), depends_on='masked_trial_log')
    resp_time_seq   = Property(Array('f'), depends_on='masked_trial_log')
    react_time_seq  = Property(Array('f'), depends_on='masked_trial_log')
    react_seq       = Property(Array('S'), depends_on='masked_trial_log')

    # The following sequences need to handle the edge case where the trial log
    # is initially empty (and has no known record fields to speak of), hence the
    # helper method below.

    def _get_masked_trial_log_field(self, field):
        try:
            return self.masked_trial_log[field]
        except:
            return np.array([])

    @cached_property
    def _get_ts_seq(self):
        return self._get_masked_trial_log_field('ts_start')

    @cached_property
    def _get_ttype_seq(self):
        return self._get_masked_trial_log_field('ttype')

    @cached_property
    def _get_resp_seq(self):
        return self._get_masked_trial_log_field('response')

    @cached_property
    def _get_resp_time_seq(self):
        return self._get_masked_trial_log_field('response_time')

    @cached_property
    def _get_react_time_seq(self):
        return self._get_masked_trial_log_field('reaction_time')

    @cached_property
    def _get_react_seq(self):
        return self._get_masked_trial_log_field('reaction')

    # Sequences of boolean indicating trial type and subject's response.

    # Trial type sequences
    go_seq      = Property(Array('b'), depends_on='masked_trial_log')
    nogo_seq    = Property(Array('b'), depends_on='masked_trial_log')

    # Response sequences
    spout_seq   = Property(Array('b'), depends_on='masked_trial_log')
    poke_seq    = Property(Array('b'), depends_on='masked_trial_log')
    nr_seq      = Property(Array('b'), depends_on='masked_trial_log')
    yes_seq     = Property(Array('b'), depends_on='masked_trial_log')

    # Reaction sequences
    late_seq    = Property(Array('b'), depends_on='masked_trial_log')
    early_seq   = Property(Array('b'), depends_on='masked_trial_log')
    normal_seq  = Property(Array('b'), depends_on='masked_trial_log')
    
    @cached_property
    def _get_yes_seq(self):
        return self.spout_seq

    @cached_property
    def _get_go_seq(self):
        return string_array_equal(self.ttype_seq, 'GO')

    @cached_property
    def _get_nogo_seq(self):
        nogo = string_array_equal(self.ttype_seq, 'NOGO') 
        nogo_repeat = string_array_equal(self.ttype_seq, 'NOGO_REPEAT') 
        return nogo ^ nogo_repeat

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

    go_indices   = Property(Array('i'), depends_on='ttype_seq')
    nogo_indices = Property(Array('i'), depends_on='ttype_seq')
    go_trial_count = Property(Int, store='attribute', depends_on='masked_trial_log')
    nogo_trial_count = Property(Int, store='attribute', depends_on='masked_trial_log')

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

    @cached_property
    def _get_go_trial_count(self):
        return np.sum(self.go_seq)

    @cached_property
    def _get_nogo_trial_count(self):
        return np.sum(self.nogo_seq)

    global_fa_frac = Property(Float, depends_on='masked_trial_log')

    @cached_property
    def _get_global_fa_frac(self):
        fa = np.sum(self.fa_seq)
        cr = np.sum(self.cr_seq)
        try:
            return fa/(fa+cr)
        except ZeroDivisionError:
            return np.nan

    hit_seq         = Property(depends_on='masked_trial_log')
    miss_seq        = Property(depends_on='masked_trial_log')
    fa_seq          = Property(depends_on='masked_trial_log')
    cr_seq          = Property(depends_on='masked_trial_log')

    @cached_property
    def _get_hit_seq(self):
        return self.go_seq & self.normal_seq & self.spout_seq

    @cached_property
    def _get_miss_seq(self):
        return self.go_seq & (self.poke_seq | self.nr_seq) & self.normal_seq

    @cached_property
    def _get_fa_seq(self):
        return (self.early_seq & self.spout_seq) | \
               (self.nogo_seq & self.normal_seq & self.spout_seq)

    @cached_property
    def _get_cr_seq(self):
        return ((self.nogo_seq & self.normal_seq) | self.early_seq) & \
                ~self.spout_seq

PositiveData = PositiveData_0_1

from __future__ import division

from abstract_experiment_data import AbstractExperimentData
from sdt_data_mixin import SDTDataMixin
from traits.api import Instance, Int, Float, \
    cached_property, Array, Property, Enum, Bool
import numpy as np
from cns.data.h5_utils import get_or_append_node

from cns.channel import FileTimeseries, FileChannel, FileEpoch
from .utils import get_temp_mic_node

import logging
log = logging.getLogger(__name__)


class PositiveData(AbstractExperimentData, SDTDataMixin):

    # VERSION is a reserved keyword in HDF5 files, so I use OBJECT_VERSION
    # instead
    OBJECT_VERSION = Float(4.1)

    mask_mode = Enum('none', 'include recent')
    mask_num = Int(25)
    masked_trial_log = Property(depends_on='mask_+, trial_log')

    # This is affected by the mask_mode and mask_num settings and cna be used to
    # adjust the subset of the trial_log that is analyzed in the on-line
    # experiment.
    def _get_masked_trial_log(self):
        if self.mask_mode == 'none':
            return self.trial_log
        else:
            # Count goes backwards from the end of the array
            if len(self.trial_log) == 0:
                return self.trial_log

            go_seq = self.string_array_equal(self.trial_log['ttype'], 'GO')
            go_number = go_seq[::-1].cumsum()
            try:
                index = np.nonzero(go_number > self.mask_num)[0][0]
                return self.trial_log[-index:]
            except IndexError:
                return self.trial_log

    c_hit = Int(0, context=True, label='Consecutive hits (excluding reminds)')
    c_fa = Int(0, context=True, label='Consecutive fas (excluding repeats)')
    c_nogo = Int(0, context=True, label='Consecutive nogos (excluding repeats)')
    c_nogo_all = Int(0, context=True, label='Consecutive nogos')
    fa_rate = Float(0, context=True, label='Running FA rate (frac)')

    microphone      = Instance(FileChannel)

    signal_epoch    = Instance(FileEpoch)
    poke_epoch      = Instance(FileEpoch)
    all_poke_epoch  = Instance(FileEpoch)
    response_ts     = Instance(FileTimeseries)

    # If True, save to datafile otherwise use a temporary file for storing the
    # mic data.
    save_microphone = Bool(False)

    def _microphone_default(self):
        if self.save_microphone:
            node = self.store_node
        else:
            node = get_temp_mic_node()
        return FileChannel(node=node, name='microphone', dtype=np.float32)

    def _trial_epoch_default(self):
        node = get_or_append_node(self.store_node, 'contact')
        return FileEpoch(node=node, name='trial_epoch')

    def _signal_epoch_default(self):
        node = get_or_append_node(self.store_node, 'contact')
        return FileEpoch(node=node, name='signal_epoch')

    def _poke_epoch_default(self):
        node = get_or_append_node(self.store_node, 'contact')
        return FileEpoch(node=node, name='poke_epoch')

    def _all_poke_epoch_default(self):
        node = get_or_append_node(self.store_node, 'contact')
        return FileEpoch(node=node, name='all_poke_epoch')

    def _response_ts_default(self):
        node = get_or_append_node(self.store_node, 'contact')
        return FileTimeseries(node=node, name='response_ts')

    def log_trial(self, **kwargs):
        AbstractExperimentData.log_trial(self, **kwargs)

        # Now, compute the context data
        normal_seq = self.nogo_normal_seq | self.go_seq
        self.c_nogo = self.rcount(self.nogo_normal_seq[normal_seq])
        self.c_nogo_all = self.rcount(self.nogo_seq)
        self.c_fa = self.rcount(self.fa_seq[self.early_seq|self.nogo_seq])
        self.fa_rate = self.fa_seq[self.early_seq|self.nogo_seq][-10:].mean()

        # We include the FA seq when slicing that way we can reset the count if
        # the gerbil false alarms (which they almost certainly do)
        self.c_hit = self.rcount(self.hit_seq[self.go_seq|self.fa_seq])

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
    nogo_normal_seq = Property(Array('b'), depends_on='masked_trial_log')
    nogo_repeat_seq = Property(Array('b'), depends_on='masked_trial_log')

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
        return self.string_array_equal(self.ttype_seq, 'GO')

    @cached_property
    def _get_nogo_normal_seq(self):
        return self.string_array_equal(self.ttype_seq, 'NOGO')

    @cached_property
    def _get_nogo_repeat_seq(self):
        return self.string_array_equal(self.ttype_seq, 'NOGO_REPEAT')

    @cached_property
    def _get_nogo_seq(self):
        return self.nogo_repeat_seq ^ self.nogo_normal_seq

    @cached_property
    def _get_poke_seq(self):
        return self.string_array_equal(self.resp_seq, 'poke')

    @cached_property
    def _get_spout_seq(self):
        return self.string_array_equal(self.resp_seq, 'spout')

    @cached_property
    def _get_nr_seq(self):
        return self.string_array_equal(self.resp_seq, 'no response')

    @cached_property
    def _get_late_seq(self):
        return self.string_array_equal(self.react_seq, 'late')

    @cached_property
    def _get_early_seq(self):
        return self.string_array_equal(self.react_seq, 'early')

    @cached_property
    def _get_normal_seq(self):
        return self.string_array_equal(self.react_seq, 'normal')

    go_indices   = Property(Array('i'), depends_on='ttype_seq')
    nogo_indices = Property(Array('i'), depends_on='ttype_seq')
    go_trial_count = Property(Int, depends_on='masked_trial_log')
    nogo_trial_count = Property(Int, depends_on='masked_trial_log')

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
        if fa+cr == 0:
            return np.nan
        return fa/(fa+cr)

    hit_seq         = Property(depends_on='masked_trial_log')
    miss_seq        = Property(depends_on='masked_trial_log')
    fa_seq          = Property(depends_on='masked_trial_log')
    cr_seq          = Property(depends_on='masked_trial_log')

    @cached_property
    def _get_hit_seq(self):
        return self.go_seq & self.spout_seq

    @cached_property
    def _get_miss_seq(self):
        return self.go_seq & (self.poke_seq | self.nr_seq)

    @cached_property

    def _get_fa_seq(self):
        return self.nogo_seq & self.spout_seq

    @cached_property
    def _get_cr_seq(self):
        return self.nogo_seq & ~self.spout_seq

    def save(self):
        # This function will be called when the user hits the stop button.  This
        # is where you save extra attributes that were not saved elsewhere.  Be
        # sure to set mask mode to none otherwise the go/nogo counts that get
        # saved in the node will be slightly incorrect.

        # Call the PositiveData superclass to save the trial log.
        self.mask_mode = 'none'
        self.store_node._v_attrs['OBJECT_VERSION'] = self.OBJECT_VERSION
        self.store_node._v_attrs['go_trial_count'] = self.go_trial_count
        self.store_node._v_attrs['nogo_trial_count'] = self.nogo_trial_count

        # Be sure to call this after you set the mask mode!
        super(PositiveData, self).save()

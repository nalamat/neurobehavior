from __future__ import division
from cns.channel import FileTimeseries, FileChannel, FileEpoch
from abstract_experiment_data import AbstractExperimentData

from enthought.traits.api import (Instance, Int, Float, cached_property,
                                  Property, Enum)

import numpy as np
from cns.data.h5_utils import get_or_append_node

from aversive_analysis_mixin import AversiveAnalysisMixin

class AversiveData(AbstractExperimentData, AversiveAnalysisMixin):
    '''
    Low-level container for data.  Absolutely no post-processing, metadata or
    analysis of this data is made.
    '''
    
    OBJECT_VERSION = Float(3.1)

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
            go_seq = self.string_array_equal(self.trial_log['ttype'], 'GO')
            go_number = go_seq[::-1].cumsum()
            try:
                index = np.nonzero(go_number > self.mask_num)[0][0]
                return self.trial_log[-index:]
            except IndexError:
                return self.trial_log

    # Safe and nogo are synonymous.  We just make both available for analysis
    # purposes.
    c_safe = Property(context=True, depends_on='trial_log')
    c_nogo = Property(context=True, depends_on='trial_log')

    #-------------------------------------------------------------------
    # Raw data
    #------------------------------------------------------------------- 
    contact_digital = Instance(FileChannel)
    contact_digital_mean = Instance(FileChannel)
    contact_analog = Instance(FileChannel)
    trial_running = Instance(FileChannel)
    shock_running = Instance(FileChannel)
    warn_running = Instance(FileChannel)

    trial_epoch     = Instance(FileEpoch)
    spout_epoch     = Instance(FileEpoch)
    reaction_ts     = Instance(FileTimeseries)

    '''
    During the addition of an optical sensor, changes were made to how the
    AversiveData object stores the contact data.  We acquired data from both
    sensors: a "touch" (for electrical) and "optical" channel.  These were
    stored under touch_digital and optical_digital, respectively.  However, old
    AversiveData objects continue to use contact_digital.  During the
    transition, I forgot to ensure that some of the new AversiveData (V2)
    objects implemented a contact_digital alias.
    '''

    def log_trial(self, **kwargs):
        kwargs['start'] = kwargs['ts_start']/self.contact_digital.fs
        kwargs['end'] = kwargs['ts_end']/self.contact_digital.fs
        AbstractExperimentData.log_trial(self, **kwargs)

    def _contact_digital_default(self):
        return self._create_channel('contact_digital', np.bool)

    def _contact_digital_mean_default(self):
        return self._create_channel('contact_digital_mean', np.float32)

    def _contact_analog_default(self):
        return self._create_channel('contact_analog', np.float32)

    def _trial_running_default(self):
        return self._create_channel('trial_running', np.bool)

    def _shock_running_default(self):
        return self._create_channel('shock_running', np.bool)

    def _warn_running_default(self):
        return self._create_channel('warn_running', np.bool)

    def _trial_epoch_default(self):
        node = get_or_append_node(self.store_node, 'contact')
        return FileEpoch(node=node, name='trial_epoch')

    def _spout_epoch_default(self):
        node = get_or_append_node(self.store_node, 'contact')
        return FileEpoch(node=node, name='spout_epoch')

    def _reaction_ts_default(self):
        node = get_or_append_node(self.store_node, 'contact')
        return FileTimeseries(node=node, name='response_ts')

    #-------------------------------------------------------------------
    # Information that does not depend on analysis parameters
    #------------------------------------------------------------------- 

    # Splits trial_log by column
    ts_start_seq    = Property(depends_on='trial_log')
    ts_end_seq      = Property(depends_on='trial_log')
    ttype_seq       = Property(depends_on='trial_log')
    safe_seq        = Property(depends_on='trial_log')
    warn_seq        = Property(depends_on='trial_log')

    @cached_property
    def _get_ts_start_seq(self):
        try:
            return self.trial_log['ts_start']
        except:
            return np.array([])

    @cached_property
    def _get_ts_end_seq(self):
        try:
            return self.trial_log['ts_end']
        except:
            return np.array([])

    @cached_property
    def _get_ttype_seq(self):
        try:
            return self.trial_log['ttype']
        except:
            return np.array([])

    @cached_property
    def _get_safe_seq(self):
        return self.string_array_equal(self.ttype_seq, 'NOGO')

    @cached_property
    def _get_warn_seq(self):
        return self.string_array_equal(self.ttype_seq, 'GO')

    par_safe_mask = Property(depends_on='trial_log, parameters')
    par_warn_mask = Property(depends_on='trial_log, parameters')

    @cached_property
    def _get_par_safe_mask(self):
        return [self.safe_seq & m for m in self.par_mask]

    @cached_property
    def _get_par_warn_mask(self):
        return [self.warn_seq & m for m in self.par_mask]

    warn_trial_count = Property(Int, depends_on='trial_log')

    @cached_property
    def _get_warn_trial_count(self):
        return np.sum(self.warn_seq)

    @cached_property
    def _get_c_safe(self):
        return self.rcount(self.safe_seq)

    safe_trial_count = Property(Int, depends_on='trial_log')

    @cached_property
    def _get_safe_trial_count(self):
        return np.sum(self.safe_seq)

    @cached_property
    def _get_c_nogo(self):
        return self.c_safe

    def save(self):
        # This function will be called when the user hits the stop button.  This
        # is where you save extra attributes that were not saved elsewhere.  Be
        # sure to set mask mode to none otherwise the go/nogo counts that get
        # saved in the node will be slightly incorrect.

        self.mask_mode = 'none'
        self.store_node._v_attrs['OBJECT_VERSION'] = self.OBJECT_VERSION
        self.store_node._v_attrs['warn_trial_count'] = self.warn_trial_count
        self.store_node._v_attrs['safe_trial_count'] = self.safe_trial_count

        # Store the contact settings
        self.store_node._v_attrs['contact_offset'] = self.contact_offset
        self.store_node._v_attrs['contact_dur'] = self.contact_dur
        self.store_node._v_attrs['contact_fraction'] = self.contact_fraction
        self.store_node._v_attrs['contact_reference'] = self.contact_reference
        fh = self.store_node._v_file

        if len(self.contact_scores):
            fh.createArray(self.store_node, 'contact_scores',
                    self.contact_scores)

        # This is what saves the trial_log and par_info table.
        super(AversiveData, self).save()

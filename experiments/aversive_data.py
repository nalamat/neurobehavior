from __future__ import division
from cns.channel import FileMultiChannel, FileChannel
from abstract_experiment_data import AbstractExperimentData

from enthought.traits.api import Instance, List, Int, Float, Any, \
    Range, DelegatesTo, cached_property, on_trait_change, Array, Event, \
    Property, Undefined, Str, Enum, Bool, DelegatesTo, HasTraits, Tuple

from datetime import datetime
import numpy as np
from cns.data.h5_utils import append_node, get_or_append_node
from scipy.stats import norm

from enthought.traits.ui.api import View

from aversive_analysis_mixin import AversiveAnalysisMixin

class RawAversiveData_v0_2(AbstractExperimentData, AversiveAnalysisMixin):
    '''
    Low-level container for data.  Absolutely no post-processing, metadata or
    analysis of this data is made.
    '''
    
    OBJECT_VERSION = Float(3, store='attribute')

    #-------------------------------------------------------------------
    # Raw data
    #------------------------------------------------------------------- 
    contact_digital = Instance(FileChannel, 
            store='channel', store_path='contact/contact_digital')
    contact_digital_mean = Instance(FileChannel, 
            store='channel', store_path='contact/contact_digital_mean')
    contact_analog = Instance(FileChannel, 
            store='channel', store_path='contact/contact_analog')
    trial_running = Instance(FileChannel, 
            store='channel', store_path='contact/trial_running')
    shock_running = Instance(FileChannel, 
            store='channel', store_path='contact/shock_running')
    warn_running = Instance(FileChannel, 
            store='channel', store_path='contact/warn_running')

    '''During the addition of an optical sensor, changes were made to how the
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
        return self.ttype_seq == 'safe'

    @cached_property
    def _get_warn_seq(self):
        return self.ttype_seq == 'warn'

    par_safe_mask = Property(depends_on='trial_log, parameters')
    par_warn_mask = Property(depends_on='trial_log, parameters')

    @cached_property
    def _get_par_safe_mask(self):
        return [self.safe_seq & m for m in self.par_mask]

    @cached_property
    def _get_par_warn_mask(self):
        return [self.warn_seq & m for m in self.par_mask]

    par_warn_count = Property(List(Int), depends_on='trial_log')
    par_safe_count = Property(List(Int), depends_on='trial_log')
    warn_trial_count = Property(Int, store='attribute', depends_on='trial_log')

    @cached_property
    def _get_par_warn_count(self):
        return self.apply_par_mask(np.sum, self.warn_seq)

    @cached_property
    def _get_par_safe_count(self):
        return self.apply_par_mask(np.sum, self.safe_seq)

    @cached_property
    def _get_warn_trial_count(self):
        return np.sum(self.warn_seq)

RawAversiveData = RawAversiveData_v0_2
AversiveData = RawAversiveData

from __future__ import division
from cns.channel import FileMultiChannel, FileChannel
from abstract_experiment_data import AbstractExperimentData

from enthought.traits.api import Instance, List, Int, Float, Any, \
    Range, DelegatesTo, cached_property, on_trait_change, Array, Event, \
    Property, Undefined, Str, Enum, Bool, DelegatesTo, HasTraits

from datetime import datetime
import numpy as np
from cns.data.h5_utils import append_node, get_or_append_node
from scipy.stats import norm

from enthought.traits.ui.api import View

def apply_mask(fun, seq, mask):
    seq = np.array(seq)
    return [fun(seq[m]) for m in mask]

# Datatype information for the various tables and lists used in this module. All
# timestamps reflect the sample number of the contact data
WATER_DTYPE = [('timestamp', 'i'), ('infused', 'f')]
TRIAL_DTYPE = [('timestamp', 'i'), ('par', 'f'), ('shock', 'f'), ('type', 'S16'), ]
EVENT_DTYPE = [('timestamp', 'i'), ('name', 'S64'), ('value', 'S128'), ]
RAW_PAR_INFO_DTYPE = [('par', 'f'), ('safe_count', 'i'), ('count', 'i')]
ANALYZED_PAR_INFO_DTYPE = [('par', 'f'), 
                           ('safe_count', 'i'),
                           ('warn_count', 'i'),
                           ('fa_count', 'i'),
                           ('hit_count', 'i'),
                           ('hit_frac', 'f'),
                           ('fa_frac', 'f'),
                           ('d', 'f'),
                           ('d_global', 'f')
                          ]

class RawAversiveData_v0_2(AbstractExperimentData):
    '''
    Low-level container for data.  Absolutely no post-processing, metadata or
    analysis of this data is made.
    '''
    
    selected = Bool(False)

    # TODO: This is a bit of a hack but I'm not sure of a better way to send the
    # datafile down the hierarchy.  We need access to this data file so we can
    # stream data to disk rather than storing it in a temporary buffer.
    store_node = Any
    contact_fs = Float

    # Whenever a new trial is added to trial_log, an updated event is fired.
    updated = Event

    #-------------------------------------------------------------------
    # Logging functions
    #------------------------------------------------------------------- 
    def log_water(self, ts, infused):
        self.water_log.append((ts, infused))

    def log_event(self, timestamp, name, value):
        self.event_log.append((timestamp, name, '%r' % value))

    def log_trial(self, timestamp, par, shock, type):
        self.trial_log.append((timestamp, par, shock, type))

    #-------------------------------------------------------------------
    # Raw data
    #------------------------------------------------------------------- 
    water_log = List(store='table', dtype=WATER_DTYPE)
    trial_log = List(store='table', dtype=TRIAL_DTYPE)
    event_log = List(store='table', dtype=EVENT_DTYPE)

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

    def _create_channel(self, name, dtype):
        contact_node = get_or_append_node(self.store_node, 'contact')
        return FileChannel(node=contact_node, fs=self.contact_fs,
                           name=name, dtype=dtype)

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

    def _get_timestamps(self):
        return np.take(self.trial_log, 0, axis=1).ravel()

    '''Since the store nodes for channels are not generated until the channel is
    actually requested, the data file should not have nodes for these channels
    when the behavior-only paradigm is run.
    '''
    physiology_fs = Float(-1)
    physiology_data = Instance(FileMultiChannel, store='automatic',
                           store_path='physiology/electrode')
    physiology_triggers = Any(store='automatic', store_path='physiology/triggers')

    def _physiology_data_default(self):
        node = get_or_append_node(self.store_node, 'physiology')
        return FileMultiChannel(node=node, fs=self.physiology_fs,
                                name='electrode', dtype=np.float32)

    def _physiology_triggers_default(self):
        description = np.recarray((0,), dtype=[('timestamp', 'i')])
        node = get_or_append_node(self.store_node, 'physiology')
        return append_node(node, 'triggers', 'table', description)

    #-------------------------------------------------------------------
    # Experiment metadata
    #------------------------------------------------------------------- 
    comment = Str('', store='attribute')
    exit_status = Enum('complete', 'partial', 'aborted', store='attribute')

    #date = Property
    #start_time = Instance(datetime, store='attribute')
    #stop_time = Instance(datetime, store='attribute')
    #duration = Property(store='attribute')
    water_infused = Property
    
    #def _get_date(self):
    #    return self.start_time.date()

    #def _get_duration(self):
    #    if self.stop_time is None:
    #        return datetime.now()-self.start_time
    #    else:
    #        return self.stop_time-self.start_time

    def _get_water_infused(self):
        try:
            return self.water_log[-1][1]
        except:
            return 0

    par_info = Property(store='table', dtype=RAW_PAR_INFO_DTYPE)

    def _get_par_info(self):
        return zip(self.pars, self.par_safe_count, self.par_warn_count)

    #-------------------------------------------------------------------
    # Information that does not depend on analysis parameters
    #------------------------------------------------------------------- 

    # Splits trial_log by column
    ts_seq = Property(Array('i'), depends_on='trial_log')
    par_seq = Property(Array('f'), depends_on='trial_log')
    ttype_seq = Property(Array('S'), depends_on='trial_log')

    # Actual position in the sequence (used in conjunction with the *_seq
    # properties to generate the score chart used in the view.
    safe_indices = Property(Array('i'), depends_on='ttype_seq')
    warn_indices = Property(Array('i'), depends_on='ttype_seq')
    remind_indices = Property(Array('i'), depends_on='ttype_seq')
    total_indices = Property(Int, depends_on='trial_log')
    safe_par_mask = Property(List(Array('b')), depends_on='trial_log')
    warn_par_mask = Property(List(Array('b')), depends_on='trial_log')
    par_warn_count = Property(List(Int), depends_on='trial_log')
    par_safe_count = Property(List(Int), depends_on='trial_log')
    pars = Property(List(Int), depends_on='trial_log')
    warn_trial_count = Property(Int, store='attribute', depends_on='trial_log')

    @cached_property
    def _get_ts_seq(self):
        return [t[0] for t in self.trial_log]

    @cached_property
    def _get_par_seq(self):
        return [t[1] for t in self.trial_log]

    @cached_property
    def _get_ttype_seq(self):
        return [t[3] for t in self.trial_log]

    @cached_property
    def _get_total_indices(self):
        return len(self.trial_log)

    def _get_indices(self, ttype):
        if len(self.ttype_seq):
            mask = np.asarray(self.ttype_seq)==ttype
            return np.flatnonzero(mask)
        else:
            return []

    @cached_property
    def _get_safe_indices(self):
        return self._get_indices('safe')

    @cached_property
    def _get_warn_indices(self):
        return self._get_indices('warn')

    @cached_property
    def _get_remind_indices(self):
        return self._get_indices('remind')

    def _get_par_mask(self, ttype):
        ttype_mask = np.array(self.ttype_seq) == ttype
        return [np.equal(self.par_seq, par) & ttype_mask for par in self.pars]

    @cached_property
    def _get_safe_par_mask(self):
        return self._get_par_mask('safe')

    @cached_property
    def _get_warn_par_mask(self):
        return self._get_par_mask('warn')

    @cached_property
    def _get_par_warn_count(self):
        return apply_mask(len, self.par_seq, self.warn_par_mask)

    @cached_property
    def _get_par_safe_count(self):
        return apply_mask(len, self.par_seq, self.safe_par_mask)

    @cached_property
    def _get_pars(self):
        # We only want to return pars for complete trials (e.g. ones for which a
        # warn was presented).
        return np.unique(np.take(self.par_seq, self.warn_indices, axis=0))

    @cached_property
    def _get_warn_trial_count(self):
        return len(self.warn_indices)

RawAversiveData = RawAversiveData_v0_2

class BaseAnalyzedAversiveData(HasTraits):
    '''
    Note that if you are attempting to compute d' and its related statistics (C,
    95% CI, etc), `cns.util.math` has standalone versions of these computations.

    Subclasses must implement
    * pars
    * par_fa_frac
    * par_hit_frac
    * global_fa_frac
    '''

    # Checkbox indicating that data should be included in analysis.  Primarily
    # for syncing with GUI
    selected = Bool(False)

    # Clip FA/HIT rate if < clip or > 1-clip (prevents unusually high z-scores)
    clip = Float(0.05, store='attribute')

    # Rather than computing a parameter-specific FA fraction, use the FA
    # fraction computed across all FA trials instead
    use_global_fa_frac = Bool(False)

    # Summary scores for the parameters.  Subclasses must implement the property
    # getters for these!
    pars = Property
    par_fa_frac = Property
    global_fa_frac = Property
    par_hit_frac = Property

    # Computed based on the summary scores provided above
    par_z_fa = Property(List(Float), depends_on='par_fa_frac')
    par_z_hit = Property(List(Float), depends_on='par_hit_frac')
    par_dprime = Property(List(Float), depends_on=['use_global_fa_frac',
                                                   'par_fa_frac',
                                                   'par_hit_frac'])
    par_dprime_nonglobal = Property(List(Float), 
                                    depends_on='par_fa_frac, par_hit_frac')
    par_dprime_global = Property(List(Float), 
                                 depends_on='par_fa_frac, par_hit_frac')

    @cached_property
    def _get_par_z_hit(self):
        par_hit_frac = np.clip(self.par_hit_frac, self.clip, 1-self.clip)
        return norm.ppf(par_hit_frac)

    @cached_property
    def _get_par_z_fa(self):
        par_fa_frac = np.clip(self.par_fa_frac, self.clip, 1-self.clip)
        return norm.ppf(par_fa_frac)

    @cached_property
    def _get_par_dprime(self):
        if self.use_global_fa_frac:
            return self.par_dprime_global
        else:
            return self.par_dprime_nonglobal

    @cached_property
    def _get_par_dprime_nonglobal(self):
        return self.par_z_hit-self.par_z_fa

    @cached_property
    def _get_par_dprime_global(self):
        return self.par_z_hit-norm.ppf(self.global_fa_frac)

    par_info = Property(store='table', dtype=ANALYZED_PAR_INFO_DTYPE)

    @cached_property
    def _get_par_info(self):
        return zip(self.pars,
                   self.par_safe_count,
                   self.par_warn_count,
                   self.par_fa_count,
                   self.par_hit_count,
                   self.par_hit_frac,
                   self.par_fa_frac, 
                   self.par_dprime_nonglobal,
                   self.par_dprime_global, )

class AnalyzedAversiveData(BaseAnalyzedAversiveData):
    '''
    Scored data from a single experiment

    False alarms and hits can only be determined after we score the data.  Prior
    to scoring the data, we must decide what trials need to be excluded: e.g.
    the subject may have been inattentive in the beginning or have grown bored
    with the task towards the end.  

    Scores contains the actual contact ratio for each trial.  False alarms and
    hits are then computed against these scores (using the contact_fraction as
    the threshold).  Scores are a fraction (0 ot 1) indicating degree of
    animal's contact with spout during the check period defined by
    `contact_offset` and `contact_dur` (relative to the trial timestamp).

    Parameters
    ----------
    exclude_first : int
        Number of trials at beginning to ignore
    exclude_last : int
        Number trials at end to ignore
    contact_offset : float (seconds)
        Start of check period relative to trial timestamp, can be a negative
        value
    contact_dur : float (seconds)
        Duration of check period
    reaction_offset : float (seconds)
        Start of snippet to extract relative to trial timestamp, can be a
        negative value
    reaction_dur : float (seconds)
        Duration of snippet to extract

    Computed properties
    -------------------
    masked_trial_log : record array
        Trial log (as record array) with trials excluded
    contact scores : array_like
        Fraction of check period that subject was in contact with spout
    contact_seq : array_like
        True/False sequence indicating whether animal was in contact with the
        spout during the check period based on `contact_fraction`.
    '''

    data = Instance(RawAversiveData, ())

    # Mask parameters
    mask_mode = Enum('none', 'exclude', 'include', store='attribute')
    exclude_first = Int(0, store='attribute')
    exclude_last = Int(0, store='attribute')
    include_last = Int(0, store='atribute')

    # Analysis parameters
    contact_offset = Float(0.9, store='attribute')
    contact_dur = Float(0.1, store='attribute')
    contact_fraction = Range(0.0, 1.0, 0.5, store='attribute')

    reaction_offset = Float(-1, store='attribute')
    reaction_dur = Float(3.0, store='attribute')

    # Masked data
    trial_log = Property(depends_on='data.trial_log')
    masked_trial_log = Property(depends_on='data.trial_log, mask_mode, exclude+, include+')

    # Basic analysis of masked data
    DEP_CONTACT = ['trial_log', 'contact_dur', 'contact_offset']
    DEP_M_CONTACT = ['masked_trial_log', 'contact_dur', 'contact_offset']
    DEP_CONTACT_SEQ = ['contact_scores', 'contact_fraction']
    DEP_M_CONTACT_SEQ = ['masked_contact_scores', 'contact_fraction']
    contact_scores = Property(depends_on=DEP_CONTACT, store='array', dtype='f')
    masked_contact_scores = Property(depends_on=DEP_M_CONTACT, store='array',
                                     dtype='f')

    contact_seq = Property(depends_on=DEP_CONTACT_SEQ, store='array',
                           dtype='bool')
    masked_contact_seq = Property(depends_on=DEP_M_CONTACT_SEQ, store='array',
                                  dtype='bool')

    # Parameter summary based on masked data
    pars = Property(depends_on='masked_trial_log')
    par_fa_count = Property(depends_on='masked_contact_seq')
    par_hit_count = Property(depends_on='masked_contact_seq')
    par_safe_count = Property(depends_on='masked_contact_seq')
    par_warn_count = Property(depends_on='masked_contact_seq')

    par_hit_frac = Property(depends_on='masked_contact_seq')
    par_fa_frac = Property(depends_on='masked_contact_seq')
    global_fa_frac = Property(depends_on='masked_contact_seq')

    # Overview information
    warn_trial_count = Property(depends_on='masked_trial_log')

    #-------------------------------------------------------------------
    # Compute masked data
    #-------------------------------------------------------------------
    @cached_property
    def _get_trial_log(self):
        return np.array(self.data.trial_log, dtype=TRIAL_DTYPE)

    @cached_property
    def _get_masked_trial_log(self):
        '''
        Convert `data.trial_log` to record array and mask unwanted trials
        '''
        log = np.array(self.data.trial_log, dtype=TRIAL_DTYPE)
        if len(log) == 0:
            return log

        warn_indices = np.flatnonzero(log['type'] == 'warn')

        if self.mask_mode == 'exclude':
            lb = warn_indices[exclude_first]
            if self.exclude_last != 0:
                ub = warn_indices[-self.exclude_last]
            else:
                ub = warn_indices[-1]
            return log[lb:ub]
        elif self.mask_mode == 'include':
            if len(warn_indices) < self.include_last:
                return log
            else:
                index = warn_indices[-self.include_last]
                return log[index:]
        else:
            return log

    safe_par_mask = Property(depends_on='masked_trial_log')
    warn_par_mask = Property(depends_on='masked_trial_log')

    def _get_pars(self):
        mask = self.masked_trial_log['type'] == 'warn'
        return np.unique(self.masked_trial_log[mask]['par'])

    def _get_par_mask(self, ttype):
        if len(self.pars):
            ttype_mask = self.masked_trial_log['type'] == ttype
            par_mask = [self.masked_trial_log['par'] == par for par in self.pars]
            return par_mask & ttype_mask
        else:
            return []

    def _get_warn_par_mask(self):
        return self._get_par_mask('warn')

    def _get_safe_par_mask(self):
        return self._get_par_mask('safe')

    #-------------------------------------------------------------------
    # Basic analysis
    #-------------------------------------------------------------------

    # Views of contact scores for the indicated trial type
    safe_scores = Property(Array(dtype='f'), depends_on='contact_scores')
    warn_scores = Property(Array(dtype='f'), depends_on='contact_scores')
    remind_scores = Property(Array(dtype='f'), depends_on='contact_scores')

    remind_indices = DelegatesTo('data')
    safe_indices = DelegatesTo('data')
    warn_indices = DelegatesTo('data')
    total_indices = DelegatesTo('data')

    contact_seq = Property(Array(dtype='b'), depends_on='contact_scores')
    fa_seq = Property(Array(dtype='f'), depends_on='contact_seq')
    hit_seq = Property(Array(dtype='f'), depends_on='contact_seq')
    remind_seq = Property(Array(dtype='f'), depends_on='contact_seq')

    #reaction_snippets = List(Array(dtype='f'))

    # Views of reaction snippet for the indicated trial type
    #safe_reaction_snippets = Property(List(Array(dtype='f')))
    #mean_safe_reaction_snippets = Property(Array(dtype='f'))
    #warn_reaction_snippets = Property(List(Array(dtype='f')))

    #par_warn_reaction_snippets = Property(List(Array(dtype='f')))
    #par_mean_warn_reaction_snippets = Property(List(Array(dtype='f')))

    #-------------------------------------------------------------------
    # Process raw data based on masks
    #------------------------------------------------------------------- 

    def _compute_contact_scores(self, trial_log):
        # Right now the algorithm assumes that you are computing from the
        # beginning of the trial and does not handle variable-length trials.
        contact = self.data.contact_digital
        lb_index = contact.to_samples(self.contact_offset)
        ub_index = contact.to_samples(self.contact_offset+self.contact_dur)

        scores = []
        for ts in trial_log['timestamp']:
            score = contact.get_range_index(lb_index, ub_index, ts).mean()
            scores.append(score)
        return scores

    @cached_property
    def _get_contact_scores(self):
        return self._compute_contact_scores(self.trial_log)

    @cached_property
    def _get_masked_contact_scores(self):
        return self._compute_contact_scores(self.masked_trial_log)

    @cached_property
    def _get_reaction_snippets(self):
        '''
        Extracts segment of contact waveform
        
        Start offset (relative to the timestamp) and duration of the segment are
        determined by `reaction_offset` and `reaction_dur`.
        '''
        contact = self.data.contact_digital
        lb_index = contact.to_samples(self.reaction_offset)
        ub_index = contact.to_samples(self.reaction_offset+self.reaction_dur)

        snippets = []
        for ts in self.masked_trial_log['timestamp']:
            snippets.append(contact.get_range_index(lb_index, ub_index, ts))
        return snippets

    #-------------------------------------------------------------------
    # Contact scores
    #------------------------------------------------------------------- 
    def _get_scores(self, indices):
        return np.take(self.contact_scores, indices)

    @cached_property
    def _get_safe_scores(self):
        return self._get_scores(self.data.safe_indices)

    @cached_property
    def _get_warn_scores(self):
        return self._get_scores(self.data.warn_indices)

    @cached_property
    def _get_remind_scores(self):
        return self._get_scores(self.data.remind_indices)

    #-------------------------------------------------------------------
    # Sequences (NOT AFFECTED BY THE INCLUDE MASK)
    #------------------------------------------------------------------- 
    @cached_property
    def _get_contact_seq(self):
        return np.array(self.contact_scores) < self.contact_fraction

    def _get_masked_contact_seq(self):
        return np.array(self.masked_contact_scores) < self.contact_fraction

    @cached_property
    def _get_fa_seq(self):
        return self.safe_scores < self.contact_fraction

    @cached_property
    def _get_hit_seq(self):
        return self.warn_scores < self.contact_fraction

    @cached_property
    def _get_remind_seq(self):
        return self.remind_scores < self.contact_fraction

    #-------------------------------------------------------------------
    # Counts
    #------------------------------------------------------------------- 
    @cached_property
    def _get_par_fa_count(self):
        return apply_mask(np.sum, self.masked_contact_seq, self.safe_par_mask)

    @cached_property
    def _get_par_hit_count(self):
        return apply_mask(np.sum, self.masked_contact_seq, self.warn_par_mask)

    @cached_property
    def _get_par_safe_count(self):
        return apply_mask(len, self.masked_contact_seq, self.safe_par_mask)

    @cached_property
    def _get_par_warn_count(self):
        return apply_mask(len, self.masked_contact_seq, self.warn_par_mask)

    #-------------------------------------------------------------------
    # Implementation of required property getters
    #------------------------------------------------------------------- 
    @cached_property
    def _get_par_fa_frac(self):
        return apply_mask(np.mean, self.masked_contact_seq, self.safe_par_mask)

    @cached_property
    def _get_global_fa_frac(self):
        mask = self.masked_trial_log['type'] == 'safe'
        return np.array(self.masked_contact_seq)[mask].mean()
    
    @cached_property
    def _get_par_hit_frac(self):
        return apply_mask(np.mean, self.masked_contact_seq, self.warn_par_mask) 

    def _get_warn_trial_count(self):
        return (self.masked_trial_log['type'] == 'warn').sum()

    #-------------------------------------------------------------------
    # Reaction snippets
    #------------------------------------------------------------------- 
    #def _get_mean_safe_reaction_snippets(self):
    #    return self.safe_reaction_snippets.mean(0)

    #def _get_safe_reaction_snippets(self):
    #    return np.take(self.reaction_snippets, self.safe_indices, axis=0)

    #def _get_par_warn_reaction_snippets(self):
    #    return apply_mask(self.reaction_snippets, self.warn_par_mask)

    #def _get_par_mean_warn_reaction_snippets(self):
    #    return [arr.mean(0) for arr in self.par_warn_reaction_snippets]

class GrandAnalyzedAversiveData(BaseAnalyzedAversiveData):
    '''
    Grand analysis using scored data from multiple experiments.  This class
    preserves the score settings for individual experiments rather than
    overriding the contact fraction, etc.
    '''
    data = List(Instance(AnalyzedAversiveData))
    filtered_data = Property(List, depends_on='+filter')

    par_safe_count = Property(List(Int), depends_on='filtered_data')
    par_warn_count = Property(List(Int), depends_on='filtered_data')
    par_hit_count = Property(List(Int), depends_on='filtered_data')
    par_fa_count = Property(List(Int), depends_on='filtered_data')

    filter = Property

    min_trials = Int(20, filter=True)

    def _get_filter(self):
        return lambda o: (o.warn_trial_count >= self.min_trials) 

    @cached_property
    def _get_filtered_data(self):
        return [d for d in self.data if self.filter(d)]

    @cached_property
    def _get_pars(self):
        pars = np.concatenate([d.pars for d in self.filtered_data])
        return np.unique(pars)

    def _get_par_count(self, item):
        cumsum = {}
        for d in self.filtered_data:
            for par, count in zip(d.pars, getattr(d, item)):
                cumsum[par] = cumsum.get(par, 0) + count
        return [v for k, v in sorted(cumsum.items())]

    @cached_property
    def _get_par_safe_count(self):
        return self._get_par_count('par_safe_count')

    @cached_property
    def _get_par_warn_count(self):
        return self._get_par_count('par_warn_count')

    @cached_property
    def _get_par_fa_count(self):
        return self._get_par_count('par_fa_count')

    @cached_property
    def _get_par_hit_count(self):
        return self._get_par_count('par_hit_count')

    @cached_property
    def _get_par_fa_frac(self):
        return np.true_divide(self.par_fa_count, self.par_safe_count)

    @cached_property
    def _get_par_hit_frac(self):
        return np.true_divide(self.par_hit_count, self.par_warn_count)

    @cached_property
    def _get_global_fa_frac(self):
        return np.sum(self.par_fa_count)/np.sum(self.par_safe_count)

class AnalyzedAversiveMaskingData(AnalyzedAversiveData):

    def _compute_contact_scores(self, trial_log):
        # You would override this function.  Right now the following line just
        # calls the superclass implementation of this function.  Delete the line
        # below once you have written your own implementation.
        super(AnalyzedAversiveMaskingData,
                self)._compute_contact_scores(trial_log)

if __name__ == '__main__':
    import tables
    f = tables.openFile('test2.h5', 'w')
    data = AversiveData(store_node=f.root)
    #analyzed = AnalyzedAversiveData(data=data)
    from cns.data.persistence import add_or_update_object
    add_or_update_object(data, f.root)

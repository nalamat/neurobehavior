"""
Data storage philosophy
=======================
There are two fundamental kinds of data, raw and derived (i.e. analyzed).  Raw
data is collected during the course of an experiment with as little processing
as possible.  Examples of raw data include traces from sensors and electrodes as
well as event times. 

Note that there isn't always a clear distinction between raw and derived data.
For example, there is some filtering on the spout contact data, optical sensor
data and neural waveforms during acquisition.

Aversive data terminology
=========================

Note that the function and variable names may be a bit ambiguous since I'm
not sure what to call the SAFE/WARN trials.  We need to agree on some sensible
terminology to avoid any confusion.  For example:

    trial
        The response to the test (warn) signal plus associated intertrial (safe)
        signal
    trial block
        All trials presented during an experiment.
"""
from __future__ import division
from cns.experiment.data.experiment_data import ExperimentData, AnalyzedData
from cns.channel import FileMultiChannel, FileChannel
from enthought.traits.api import Instance, List, Int, Float, Any, \
    Range, DelegatesTo, cached_property, on_trait_change, Array, Event, \
    Property, Undefined, Str, Enum, Bool
from datetime import datetime
import numpy as np
from cns.data.h5_utils import append_node, get_or_append_node
from scipy.stats import norm

from enthought.traits.ui.api import View

def apply_mask(fun, seq, mask):
    #seq = np.array(seq).ravel()
    seq = np.array(seq)
    #return [fun(np.take(seq, m)) for m in mask]
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

class RawAversiveData_v0_2(ExperimentData):
    '''
    Low-level container for data.  Absolutely no post-processing, metadata or
    analysis of this data is made.
    '''
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
        self.water_log.append([(ts, infused)])

    def log_event(self, timestamp, name, value):
        self.event_log.append([(timestamp, name, '%r' % value)])

    def log_trial(self, timestamp, par, shock, type):
        self.trial_log.append([(timestamp, par, shock, type)])
        self.updated = timestamp

    #-------------------------------------------------------------------
    # Raw data in it's purest, most unaltered form
    #------------------------------------------------------------------- 
    water_log = List(store='table', dtype=WATER_DTYPE)
    trial_log = List(store='table', dtype=TRIAL_DTYPE)
    event_log = List(store='table', dtype=EVENT_DTYPE)

    # TODO: These seem like a hack, but I am not sure of a better way to
    # indicate store node and location.

    touch_digital = Instance(FileChannel, 
            store='channel', store_path='contact/touch_digital')
    touch_digital_mean = Instance(FileChannel, 
            store='channel', store_path='contact/touch_digital_mean')
    touch_analog = Instance(FileChannel, 
            store='channel', store_path='contact/touch_analog')
    optical_digital = Instance(FileChannel, 
            store='channel', store_path='contact/optical_digital')
    optical_digital_mean = Instance(FileChannel, 
            store='channel', store_path='contact/optical_digital_mean')
    optical_analog = Instance(FileChannel, 
            store='channel', store_path='contact/optical_analog')
    trial_running = Instance(FileChannel, 
            store='channel', store_path='contact/trial_running')

    '''During the addition of an optical sensor, changes were made to how the
    AversiveData object stores the contact data.  We acquired data from both
    sensors: a "touch" (for electrical) and "optical" channel.  These were
    stored under touch_digital and optical_digital, respectively.  However, old
    AversiveData objects continue to use contact_digital.  During the
    transition, I forgot to ensure that some of the new AversiveData (V2)
    objects implemented a contact_digital alias.
    '''
    contact_digital = Property
    contact_digital_mean = Property

    def _get_contact_digital(self):
        return self.touch_digital

    def _get_contact_digital_mean(self):
        return self.touch_digital_mean

    def _create_channel(self, name, dtype):
        contact_node = get_or_append_node(self.store_node, 'contact')
        return FileChannel(node=contact_node, fs=self.contact_fs,
                           name=name, dtype=dtype)

    def _contact_digital_default(self):
        return self._create_channel('contact_digital', np.bool)

    def _contact_digital_mean_default(self):
        return self._create_channel('contact_digital_mean', np.float32)

    def _touch_digital_default(self):
        return self._create_channel('touch_digital', np.bool)

    def _touch_digital_mean_default(self):
        return self._create_channel('touch_digital_mean', np.float32)

    def _touch_analog_default(self):
        return self._create_channel('touch_analog', np.float32)

    def _optical_digital_default(self):
        return self._create_channel('optical_digital', np.bool)

    def _optical_digital_mean_default(self):
        return self._create_channel('optical_digital_mean', np.float32)

    def _optical_analog_default(self): 
        return self._create_channel('optical_analog', np.float32)

    def _trial_running_default(self):
        return self._create_channel('trial_running', np.bool)

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
    date = Property
    start_time = Instance(datetime, store='attribute')
    stop_time = Instance(datetime, store='attribute')
    duration = Property(store='attribute')
    water_infused = Property
    
    def _get_date(self):
        return self.start_time.date()

    def _get_duration(self):
        if self.stop_time is None:
            return datetime.now()-self.start_time
        else:
            return self.stop_time-self.start_time

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

    ts_seq = Property(Array('i'))
    par_seq = Property(Array('f'))
    ttype_seq = Property(Array('S'))
    # Actual position in the sequence (used in conjunction with the *_seq
    # properties to generate the score chart used in the view.
    safe_indices = Property(Array('i'))
    warn_indices = Property(Array('i'))
    remind_indices = Property(Array('i'))
    total_indices = Property(Int)
    safe_trials = Property(Array('f'))
    warn_trials = Property(Array('f'))
    safe_par_mask = Property(List(Array('b')))
    warn_par_mask = Property(List(Array('b')))
    par_warn_count = Property(List(Int))
    par_safe_count = Property(List(Int))
    pars = Property(List(Int))
    total_trials = Property(Int, store='attribute')

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

    @cached_property
    def _get_safe_trials(self):
        return np.take(self.trial_log, self.safe_indices, axis=0)

    @cached_property
    def _get_warn_trials(self):
        return np.take(self.trial_log, self.warn_indices, axis=0)

    @cached_property
    def _get_par_mask(self, trials):
        trial_pars = np.take(trials, [1], axis=1).ravel()
        return [trial_pars == par for par in self.pars]

    @cached_property
    def _get_safe_par_mask(self):
        return self._get_par_mask(self.safe_trials)

    @cached_property
    def _get_warn_par_mask(self):
        return self._get_par_mask(self.warn_trials)

    @cached_property
    def _get_par_warn_count(self):
        return apply_mask(len, self.warn_trials, self.warn_par_mask)

    @cached_property
    def _get_par_safe_count(self):
        return apply_mask(len, self.safe_trials, self.safe_par_mask)

    @cached_property
    def _get_pars(self):
        return np.unique(self.par_seq)
        #return np.unique(np.take(self.warn_trials, [1], axis=1).ravel())

    @cached_property
    def _get_total_trials(self):
        return len(self.warn_trials)

RawAversiveData = RawAversiveData_v0_2

class BaseAnalyzedAversiveData(AnalyzedData):
    '''
    Note that if you are attempting to compute d' and its related statistics (C,
    95% CI, etc), `cns.util.math` has standalone versions of these computations.
    '''

    # Clip FA/HIT rate if < clip or > 1-clip (prevents unusually high z-scores)
    clip = Float(0.05, store='attribute')

    # Rather than computing a parameter-specific FA fraction, use the FA
    # fraction computed across all FA trials instead
    use_global_fa_frac = Bool(False)

    # Summary scores for the parameters.  Subclasses must implement the property
    # getters for these!
    pars = Property(List(Float))
    par_fa_frac = Property(List(Float), depends_on='updated')
    global_fa_frac = Property(Float, depends_on='updated', store='attribute')
    par_hit_frac = Property(List(Float), depends_on='updated')

    # Computed based on the summary scores provided above
    par_z_fa = Property(List(Float), depends_on='updated')
    par_z_hit = Property(List(Float), depends_on='updated')
    par_dprime = Property(List(Float), depends_on='updated, use_global_fa_frac')
    par_dprime_nonglobal = Property(List(Float), depends_on='updated')
    par_dprime_global = Property(List(Float), depends_on='updated')

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
    '''

    updated = Event

    data = Instance(RawAversiveData)

    # The next few pars will influence the analysis of the data, specifically
    # the "score".  Anytime these change, the data must be reanalyzed.
    contact_offset = Float(0.9, store='attribute', label='Contact offset (s)')
    contact_dur = Float(0.1, store='attribute', label='Contact duration (s)')
    contact_fraction = Range(0.0, 1.0, 0.5, store='attribute', 
                             label='Contact fraction (s)')
    reaction_offset = Float(-1, store='attribute', label='Reaction offset',
                            unit='s')
    reaction_dur = Float(3.0, store='attribute', label='Reaction duration',
                         unit='s')

    # False alarms and hits can only be determined after we score the data.
    # Scores contains the actual contact ratio for each trial.  False alarms and
    # hits are then computed against these scores (using the contact_fraction as
    # the threshold).  Scores are a fraction (0 ot 1) indicating degree of
    # animal's contact with spout during the check period defined by
    # `contact_offset` and `contact_dur` (relative to the trial timestamp).
    contact_scores = List(Float, store='array')

    # Views of contact scores for the indicated trial type
    safe_scores = Property(Array(dtype='f'), depends_on='updated')
    warn_scores = Property(Array(dtype='f'), depends_on='updated')
    remind_scores = Property(Array(dtype='f'), depends_on='updated')

    # True/False sequence indicating whether animal was in contact with the
    # spout during the check based on `contact_fraction`.
    fa_seq = Property(Array(dtype='f'), depends_on='updated')
    hit_seq = Property(Array(dtype='f'), depends_on='updated')
    remind_seq = Property(Array(dtype='f'), depends_on='updated')

    par_fa_count = Property(Array(dtype='i'))
    par_hit_count = Property(Array(dtype='i'))

    reaction_snippets = List(Array(dtype='f'))

    # Views of reaction snippet for the indicated trial type
    safe_reaction_snippets = Property(List(Array(dtype='f')))
    mean_safe_reaction_snippets = Property(Array(dtype='f'))
    warn_reaction_snippets = Property(List(Array(dtype='f')))

    par_warn_reaction_snippets = Property(List(Array(dtype='f')))
    par_mean_warn_reaction_snippets = Property(List(Array(dtype='f')))

    def _get_mean_safe_reaction_snippets(self):
        return self.safe_reaction_snippets.mean(0)

    def _get_safe_reaction_snippets(self):
        return np.take(self.reaction_snippets, self.safe_indices, axis=0)

    def _get_warn_reaction_snippets(self):
        return np.take(self.reaction_snippets, self.warn_indices, axis=0)

    def _get_par_warn_reaction_snippets(self):
        return apply_mask(lambda x: x, self.warn_reaction_snippets,
                          self.data.warn_par_mask)

    def _get_par_mean_warn_reaction_snippets(self):
        return [arr.mean(0) for arr in self.par_warn_reaction_snippets]

    #-------------------------------------------------------------------
    # Contact scores
    #------------------------------------------------------------------- 
    def _get_scores(self, indices):
        # We need to check curidx to see if there are any contact scores.  If
        # curidx is 0, this means that code somewhere has requested the value of
        # these properties before any data is available. 
        #if len(self.contact_scores) == 0:
        #    return np.array([])
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
    # Sequences
    #------------------------------------------------------------------- 
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
        return apply_mask(np.sum, self.fa_seq, self.data.safe_par_mask)

    @cached_property
    def _get_par_hit_count(self):
        return apply_mask(np.sum, self.hit_seq, self.data.warn_par_mask)

    par_safe_count = DelegatesTo('data')
    par_warn_count = DelegatesTo('data')

    #-------------------------------------------------------------------
    # Implementation of required property getters
    #------------------------------------------------------------------- 
    pars = DelegatesTo('data')

    @cached_property
    def _get_par_fa_frac(self):
        return apply_mask(np.mean, self.fa_seq, self.data.safe_par_mask)

    @cached_property
    def _get_global_fa_frac(self):
        return self.fa_seq.mean()
    
    @cached_property
    def _get_par_hit_frac(self):
        return apply_mask(np.mean, self.hit_seq, self.data.warn_par_mask)

    #-------------------------------------------------------------------
    # Reaction snippets
    #------------------------------------------------------------------- 
    def reaction_snippet(self, ts):
        '''Extracts segment of contact waveform
        
        Start offset (relative to the timestamp) and duration of the segment are
        determined by `reaction_offset` and `reaction_dur`.
        '''
        contact = self.data.contact_digital
        lb_index = contact.to_samples(self.reaction_offset)
        ub_index = contact.to_samples(self.reaction_offset+self.reaction_dur)
        return contact.get_range_index(lb_index, ub_index, ts)

    #-------------------------------------------------------------------
    # Process incoming data
    #------------------------------------------------------------------- 
    @on_trait_change('data.updated')
    def process_timestamp(self, timestamp):
        # Check if timestamp is undefined.  When the class is first initialized,
        # we recieve a data.updated event with a value of Undefined.
        if timestamp is not Undefined:
            self.contact_scores.append(self.score_timestamp(timestamp))
            self.reaction_snippets.append(self.reaction_snippet(timestamp))
            self.updated = True

    def score_timestamp(self, ts):
        '''Computes contact score for timestamp
        '''
        contact = self.data.contact_digital
        lb_index = contact.to_samples(self.contact_offset)
        ub_index = contact.to_samples(self.contact_offset+self.contact_dur)
        return contact.get_range_index(lb_index, ub_index, ts).mean()

    @on_trait_change('data, contact_offset, contact_dur, contact_fraction')
    def reprocess_contact_scores(self):
        self.contact_scores = []
        for ts in self.data.ts_seq:
            self.contact_scores.append(self.score_timestamp(ts))
        self.updated = True

    @on_trait_change('data, reaction_offset, reaction_dur')
    def reprocess_reaction_snippets(self):
        self.reaction_snippets = []
        for ts in self.data.ts_seq:
            self.reaction_snippets.append(self.reaction_snippet(ts))
        self.updated = True

class GrandAnalyzedAversiveData(BaseAnalyzedAversiveData):
    '''
    Grand analysis using scored data from multiple experiments.  This class
    preserves the score settings for individual experiments rather than
    overriding the contact fraction, etc.
    '''
    data = List(Instance(AnalyzedAversiveData))

    par_safe_count = Property(List(Int), depends_on='updated')
    par_warn_count = Property(List(Int), depends_on='updated')
    par_hit_count = Property(List(Int), depends_on='updated')
    par_fa_count = Property(List(Int), depends_on='updated')

    @cached_property
    def _get_pars(self):
        pars = np.concatenate([d.pars for d in self.data])
        return np.unique(pars)

    def _get_par_count(self, item):
        cumsum = {}
        for d in self.data:
            for par, count in zip(d.pars, getattr(d, item)):
                cumsum[par] = cumsum.get(par, 0) + count
        return [v for k, v in sorted(cumsum.items())]

    @cached_property
    def _get_par_safe_count(self):
        print 'getting'
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
        return np.divide(self.par_fa_count, self.par_safe_count)

    @cached_property
    def _get_par_hit_frac(self):
        return np.divide(self.par_hit_count, self.par_warn_count)

    @cached_property
    def _get_global_fa_frac(self):
        return np.concatenate([d.fa_seq for d in self.data]).mean()

if __name__ == '__main__':
    import tables
    f = tables.openFile('test2.h5', 'w')
    data = AversiveData(store_node=f.root)
    #analyzed = AnalyzedAversiveData(data=data)
    from cns.data.persistence import add_or_update_object
    add_or_update_object(data, f.root)

from .experiment_controller import ExperimentController
from cns import choice, equipment
from cns.data.h5_utils import append_node, append_date_node, \
    get_or_append_node
from cns.data.persistence import add_or_update_object
from cns.experiment.data import AversiveData
from cns.experiment.paradigm.aversive_paradigm import AversiveParadigm
from datetime import timedelta, datetime
from enthought.pyface.api import error
from enthought.pyface.timer.api import Timer
from enthought.traits.api import Any, Instance, CInt, CFloat, Str, Float, \
    Property, HasTraits, Bool, on_trait_change, Dict, Button, Event
from enthought.traits.ui.api import HGroup, spring, Item, View
import logging
import time
import numpy as np

log = logging.getLogger(__name__)

class BaseCurrentSettings(HasTraits):

    paradigm = Instance(AversiveParadigm)
    
    '''Tracks the trial index for comparision with the circuit index'''
    idx = CInt(0)

    '''Number of safe trials''' 
    safe_trials = CInt
    '''The trial we are going to, or currently, presenting'''
    trial = CInt

    '''Parameter to present'''
    par = CFloat
    par_remind = CFloat

    _choice_num_safe = Any
    _choice_par = Any

    _signal_warn_cache = {}
    signal_warn = Property
    signal_remind = Property

    def __init__(self, **kw):
        super(CurrentSettings, self).__init__(**kw)
        self.initialize(self.paradigm)

    def reset(self):
        self.initialize(self.paradigm)

    def initialize(self, paradigm):
        self._choice_par = self._get_choice_par(paradigm)
        self._choice_num_safe = self._get_choice_num_safe(paradigm)
        self.build_signal_cache(paradigm)
        self.par_remind = paradigm.par_remind
        self.next()

    def next(self):
        self.par = self._choice_par.next()
        self.safe_trials = self._choice_num_safe.next()
        self.trial = 1
        #self.shock_level = self.paradigm.shock_settings.get_level(self.par)

    #===========================================================================
    # Helpers for run-time control of experiment
    #===========================================================================
    def _get_signal_warn(self):
        return self._signal_warn_cache[self.par]

    def _get_signal_remind(self):
        return self._signal_warn_cache[self.par_remind]

    def _get_choice_num_safe(self, paradigm):
        trials = range(paradigm.min_safe, paradigm.max_safe + 1)
        return choice.get('pseudorandom', trials)

    def _get_choice_par(self, paradigm):
        # Always pass a copy of pars to other functions that may modify the
        # content of the list
        return choice.get(paradigm.par_order, paradigm.pars[:])

    def _generate_signal(self, template, parameter):
        signal = template.__class__()
        errors = signal.copy_traits(template)
        if errors:
            raise BaseException('Unable to copy traits to new signal')
        signal.set_variable(parameter)
        return signal

    def build_signal_cache(self, paradigm):
        self._signal_warn_cache = {}
        for par in paradigm.pars:
            signal = self._generate_signal(paradigm.signal_warn, par)
            self._signal_warn_cache[par] = signal
        signal = self._generate_signal(paradigm.signal_warn, paradigm.par_remind)
        self._signal_warn_cache[paradigm.par_remind] = signal


class BaseAversiveController(ExperimentController):
    """Primary controller for TDT System 3 hardware.  This class must be
    configured with a model that contains the appropriate parameters (e.g.
    Paradigm) and a view to show these parameters.

    As changes are applied to the view, the necessary changes to the hardware
    (e.g. RX6 tags and PA5 attenuation) will be made and the model will be
    updated.

    For a primer on model-view-controller architecture and its relation to the
    Enthought libraries (e.g. Traits), refer to the Enthought Tool Suite
    documentation online at:
    https://svn.enthought.com/enthought/wiki/UnderstandingMVCAndTraitsUI
    """

    circuits = { 'circuit': ('aversive-behavior', 'RX6') }

    parameter_map = {'lick_th': 'circuit.lick_th',
                     'shock_duration': 'circuit.shock_n',
                     'shock_delay': 'circuit.shock_delay_n',
                     'requested_lick_fs': 'circuit.lick_nPer',
                     'contact_method': 'handler._apply_contact_method', }

    backend = Any
    pump = Any

    exp_node = Any
    data_node = Any

    # Will be used to poll the state of the hardware every few milliseconds and
    # update the view as needed (i.e. download lick data, upload new signal
    # waveforms, etc).  See timer_tick.
    fast_timer = Instance(Timer)
    slow_timer = Instance(Timer)

    # These are variables tracked by the controller to assist with providing
    # feedback to the user via the view.  While these could be stored in the
    # model (i.e. the paradigm object), they are transient variables that are
    # needed to track the system's state (i.e. what trial number are we on and
    # what is the next parameter that needs to be presented) and are not needed
    # once the experiment is done.  A good rule of thumb: if the parameter is
    # used as a placeholder for transient data (to better compute variables
    # needed for the view), it should be left out of the "model".  Hence, we
    # keep them here instead.
    current = Instance(CurrentSettings)

    # A coroutine pipeline that acquires contact data from the RX6 and sends it
    # to the TrialData object
    data_pipe = Any
    start_time = Float
    completed = Bool(False)
    water_infused = Float(0)

    status = Property(Str, depends_on='current.trial, current.par, current.safe_trials, state')
    time_elapsed = Property(Str, depends_on='slow_tick', label='Time')

    slow_tick = Event
    fast_tick = Event

    def post_init(self, info):
        '''Called after circuit has been loaded and DSP tags have been
        auto-configured.  Place paradigm-specific initialization code here.
        '''
        self.pump = equipment.pump().Pump()
        self.backend = equipment.dsp()
        self.circuit.contact_buf.intialize(channels=7, sf=127, src_type=np.int8,
                                           compression='decimated',
                                           fs=self.circuit.lick_nPer.get('fs'))
        model.exp_node = append_date_node(self.model.store_node,
                                          pre='aversive_date_')
        model.data_node = append_node(self.model.exp_node, 'Data')
        model.data = AversiveData(contact_fs=self.circuit.lick_nPer.get('fs'),
                                  store_node=self.model.data_node)

    def start(self, info=None):
        if not self.model.paradigm.is_valid():
            mesg = 'Please correct the following errors first:\n'
            mesg += self.model.paradigm.err_messages()
            error(self.info.ui.control, mesg)
            return

        try:
            self.initialize_experiment()
            self.fast_timer = Timer(250, self.tick, 'fast')
            self.slow_timer = Timer(1000, self.tick, 'slow')
            self.pause()

            self.model.data.start_time = datetime.now()
            self.circuit.start()
            self.model.trial_blocks += 1

        except BaseException, e:
            self.state = 'halted'
            error(self.info.ui.control, str(e))
            raise

    def remind(self, info=None):
        self.state = 'manual'
        self._apply_signal_remind(info)
        self.circuit.pause_state.value = False
        self.circuit.trigger(2)
        self.circuit.trigger(1)

    def pause(self, info=None):
        self.model.data.log_event(self.circuit.ts_n.value, 'pause', True)
        self.state = 'paused'
        self.circuit.pause_state.value = True

    def resume(self, info=None):
        self.model.data.log_event(self.circuit.ts_n.value, 'pause', False)
        self.state = 'running'
        self.circuit.pause_state.value = False
        self.circuit.trigger(1)

    def stop(self, info=None):
        self.state = 'halted'
        self.slow_timer.stop()
        self.fast_timer.stop()
        self.circuit.stop()
        self.pending_changes = {}
        self.old_values = {}

        self.model.data.stop_time = datetime.now()

        # Gather post-experiment information
        view = View(Item('comment', style='custom'), 'exit_status', 
                    height=200, width=300, 
                    buttons=['OK'], 
                    kind='livemodal')

        self.model.data.edit_traits(parent=info.ui.control, view=view)

        # Save the data in our newly created node
        add_or_update_object(self.pump, self.model.exp_node, 'Pump')
        add_or_update_object(self.model.paradigm, self.model.exp_node, 'Paradigm')
        add_or_update_object(self.model.data, self.model.exp_node, 'Data')
        analyzed_node = get_or_append_node(self.model.data.store_node, 'Analyzed')
        add_or_update_object(self.model.analyzed, analyzed_node)

    #===========================================================================
    # Tasks driven by the slow and fast timers
    #===========================================================================
    @on_trait_change('slow_tick')
    def task_update_pump(self):
        infused = self.pump.infused
        self.model.data.log_water(self.circuit.ts_n.value, infused)
        self.water_infused = infused
        
    @on_trait_change('fast_tick')
    def task_update_data(self):
        self.model.data.contact_data.send(self.circuit.contact_buf.read())

    @on_trait_change('fast_tick')
    def task_monitor_circuit(self):
        if self.circuit.idx.value > self.current.idx:
            self.current.idx += 1
            ts = self.circuit.lick_ts_trial_start_n.value

            # Process "reminder" signals
            if self.state == 'manual':
                self.pause()
                self.model.data.update(ts,
                                       self.current.par_remind,
                                       self.current.shock_remind,
                                       'remind')
                self._apply_signal_warn()

            # Warning was just presented.
            else:
                last_trial = self.current.trial
                self.current.trial += 1     # reminders do not count
                # We are now looking at the current trial that will be presented.  
                # What do we need to do to get ready?
                
                if last_trial == self.current.safe_trials + 1:
                    log.debug('processing warning trial')
                    self.model.data.update(ts,
                                           self.current.par,
                                           self.current.shock_warn,
                                           'warn')
                    self.current.next()
                elif last_trial == self.current.safe_trials: 
                    self.model.data.update(ts, self.current.par, 0, 'safe')
                    self._apply_signal_warn()
                    self.circuit.trigger(2)
                elif last_trial < self.current.safe_trials:
                    self.model.data.update(ts, self.current.par, 0, 'safe')
                else:
                    raise SystemError, 'There is a mismatch.'
                    # TODO: Data has not been lost so we should not halt
                    # execution.  However an appropriate warning should be sent.
                    
            # Signal to the circuit that data processing is done and it can
            # commence execution
            self.circuit.trigger(1)

    def _get_time_elapsed(self):
        if self.state is 'halted':
            return '%s' % timedelta()
        else:
            return '%s' % self.model.data.duration

    def _get_status(self):
        if self.state == 'disconnected':
            return 'Cannot connect to equipment'
        if self.state == 'halted':
            return 'System is halted'
        if self.state == 'manual':
            return 'PAUSED: presenting reminder (%r)' % self.current.par

        if self.current.trial > self.current.safe_trials:
            status = 'WARNING (%r)' % self.current.par
        else:
            mesg = 'SAFE %d of %d (%r)'
            status = mesg % (self.current.trial, self.current.safe_trials, self.current.par)
        if self.state == 'paused':
            status = 'PAUSED: next trial is %s' % status
        return status

    @on_trait_change('pump.rate')
    def log_pump(self, new):
        if self.state <> 'halted':
            self.model.data.log_event(self.circuit.ts_n.value, 'pump rate', new)

    count = CInt(0)

    ############################################################################
    # Code to apply parameter changes
    ############################################################################
    def log_event(self, ts, name, value):
        self.model.data.log_event(ts, name, value)

    def _reset_current(self, value):
        self.current.reset()

    _apply_par_order = _reset_current
    _apply_par_remind = _reset_current
    _apply_pars = _reset_current

    def _apply_contact_method(self, value):
        if value == 'touch':
            self.circuit.contact_method.value = 0
        else:
            self.circuit.contact_method.value = 1

class AversiveController(BaseAversiveController):
    parameter_map = {'signal_warn': 'handler._apply_signal_warn',
                     'signal_safe': 'handler._apply_signal_safe'}
    parameter_map.update(BaseAversiveController.parameter_map)

    @on_trait_change('fast_tick')
    def task_monitor_signal_safe(self):
        if self.circuit.int_buf.block_processed():
            samples = self.model.paradigm.signal_safe.read_block()
            self.circuit.int_buf.write(samples)
    
    def _apply_signal_remind(self):
        # The actual sequence is important.  We must finish uploading the signal
        # before we set the circuit flags to allow commencement of a trial.
        self.circuit.trial_buf.set(self.current.signal_remind)
        self.backend.set_attenuation(self.current.signal_remind.attenuation, 'PA5')

    def _apply_signal_warn(self):
        self.circuit.trial_buf.set(self.current.signal_warn)
        self.backend.set_attenuation(self.current.signal_warn.attenuation,
                                     'PA5')

    def post_init(self, info):
        super(AversiveController, self).post_init(info)
        self.current = CurrentSettings(paradigm=self.model.paradigm)
        self.circuit._apply_signal_warn(self)

class AversiveFMController(BaseAversiveController):
    parameter_map = {'center_frequency': 'circuit.cf',
                     'attenuation': 'handler._apply_attenuation'}
    parameter_map.update(BaseAversiveController.parameter_map)

    def _apply_signal_warn(self):
        self.circuit.depth.value = self.current.par

    def _apply_signal_remind(self):
        self.circuit.depth.value = self.current.par_remind

    def _apply_attenuation(self, value):
        self.backend.set_attenuation(value)
        self.circuit._apply_signal_warn(self)

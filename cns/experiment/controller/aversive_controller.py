from .experiment_controller import ExperimentController
from cns import choice, equipment
from cns.pipeline import deinterleave
from cns.data.h5_utils import append_node, append_date_node, \
    get_or_append_node
from cns.data.persistence import add_or_update_object
from cns.experiment.data.aversive_data import RawAversiveData as AversiveData
from cns.experiment.paradigm.aversive_paradigm import BaseAversiveParadigm
from datetime import timedelta, datetime
from enthought.pyface.api import error
from enthought.pyface.timer.api import Timer
from enthought.traits.api import Any, Instance, Int, Float, Str, Float, \
    Property, HasTraits, Bool, on_trait_change, Dict, Button, Event, Range
from enthought.traits.ui.api import HGroup, spring, Item, View
import logging
import time
import numpy as np

def generate_signal(template, parameter):
    signal = template.__class__()
    errors = signal.copy_traits(template)
    if errors:
        raise BaseException('Unable to copy traits to new signal')
    signal.set_variable(parameter)
    return signal

log = logging.getLogger(__name__)

class BaseAversiveController(ExperimentController):

    circuit = Any
    
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
    current_idx = Int(0)
    current_num_safe = Int
    current_trial = Int
    current_par = Float
    current_par_remind = Float
    current_par_safe = Float
    current_safe = Any

    choice_num_safe = Any
    choice_par = Any

    # A coroutine pipeline that acquires contact data from the RX6 and sends it
    # to the TrialData object
    data_pipe = Any

    #start_time = Float
    completed = Bool(False)
    water_infused = Float(0)

    status = Property(Str, depends_on='state, current_+')
    time_elapsed = Property(Str, depends_on='slow_tick', label='Time')

    slow_tick = Event
    fast_tick = Event

    def init_current(self, info=None):
        paradigm = self.model.paradigm
        self.choice_par = choice.get(paradigm.par_order, paradigm.pars[:])
        trials = range(paradigm.min_safe, paradigm.max_safe + 1)
        self.choice_num_safe = choice.get('pseudorandom', trials)

        # Refresh experiment state
        self.current_par_remind = paradigm.par_remind
        self.current_safe = paradigm.par_safe
        self.current_par = self.choice_par.next()
        self.current_num_safe = self.choice_num_safe.next()
        self.current_trial = 1

        self._apply_signal_safe()

    def init_equipment(self, info):
        log.debug('init_equipment')
        super(BaseAversiveController, self).init_equipment(info)
        self.pump = equipment.pump().Pump()

    def init_experiment(self, info):
        log.debug('init_experiment')
        super(BaseAversiveController, self).init_experiment(info)

        self.model.exp_node = append_date_node(self.model.store_node,
                                               pre='aversive_date_')
        log.debug('Created experiment node for experiment at %r',
                  self.model.exp_node)
        self.model.data_node = append_node(self.model.exp_node, 'Data')
        log.debug('Created data node for experiment at %r', self.model.data_node)
        self.model.data = AversiveData(contact_fs=self.circuit.lick_nPer.get('fs'),
                                       store_node=self.model.data_node)
        self.init_current(info)

    def start_experiment(self, info):
        self.fast_timer = Timer(250, self.tick, 'fast')
        self.slow_timer = Timer(1000, self.tick, 'slow')
        self.pause()
        self.model.data.start_time = datetime.now()
        self.circuit.start()

    def remind(self, info=None):
        self.state = 'manual'
        self._apply_signal_remind()
        self.circuit.pause_state.value = False
        self.circuit.trigger(2) # Tell circuit next trial is a warn
        self.circuit.trigger(1) # Tell circuit to go

    def pause(self, info=None):
        self.model.data.log_event(self.circuit.ts_n.value, 'pause', True)
        self.state = 'paused'
        self.circuit.pause_state.value = True

    def resume(self, info=None):
        self.model.data.log_event(self.circuit.ts_n.value, 'pause', False)
        self.state = 'running'
        self.circuit.pause_state.value = False
        self.circuit.trigger(1)

    def stop_experiment(self, info=None):
        self.state = 'halted'

        try:
            self.slow_timer.stop()
            self.fast_timer.stop()
        except AttributeError:
            self.slow_timer.Stop()
            self.fast_timer.Stop()

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
        if self.circuit.idx.value > self.current_idx:
            self.current_idx += 1
            ts = self.circuit.lick_ts_trial_start_n.value

            # Process "reminder" signals
            if self.state == 'manual':
                self.pause()
                par = self.current_par_remind
                self.model.data.log_trial(ts, par, -1, 'remind')
                self._apply_signal_warn()

            # Warning was just presented.
            else:
                last_trial = self.current_trial
                self.current_trial += 1     # reminders do not count
                # We are now looking at the current trial that will be presented.  
                # What do we need to do to get ready?
                
                if last_trial == self.current_num_safe + 1:
                    log.debug('processing warning trial')
                    self.model.data.log_trial(ts, self.current_par, -1, 'warn')
                    self.current_num_safe = self.choice_num_safe.next()
                    self.current_par = self.choice_par.next()
                    self.current_trial = 1
                    log.debug('new num_safe %d, new par %f',
                              self.current_num_safe, self.current_par)
                elif last_trial == self.current_num_safe: 
                    self.model.data.log_trial(ts, self.current_par, 0, 'safe')
                    self._apply_signal_warn()
                    self.circuit.trigger(2)
                elif last_trial < self.current_num_safe:
                    self.model.data.log_trial(ts, self.current_par, 0, 'safe')
                else:
                    log.debug('last_trial: %d, current_num_safe %d', last_trial,
                              self.current_num_safe)
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
            return 'PAUSED: presenting reminder (%r)' % self.current_par

        if self.current_trial > self.current_num_safe:
            status = 'WARNING (%r)' % self.current_par
        else:
            mesg = 'SAFE %d of %d (%r)'
            status = mesg % (self.current_trial, self.current_num_safe, self.current_par)
        if self.state == 'paused':
            status = 'PAUSED: next trial is %s' % status
        return status

    @on_trait_change('pump.rate')
    def log_pump(self, new):
        if self.state <> 'halted':
            self.model.data.log_event(self.circuit.ts_n.value, 'pump rate', new)

    #count = CInt(0)

    contact_pipe = Any

    def _contact_pipe_default(self):
        targets = [self.model.data.contact_digital,
                   self.model.data.contact_digital_mean,
                   self.model.data.trial_running, 
                   self.model.data.contact_analog ]
        return deinterleave(targets)

    ############################################################################
    # Code to apply parameter changes
    ############################################################################
    def log_event(self, ts, name, value):
        self.model.data.log_event(ts, name, value)

    def _reset_current(self, value):
        self.init_current()

    _apply_par_order = _reset_current
    _apply_par_remind = _reset_current
    _apply_pars = _reset_current

    def _apply_contact_method(self, value):
        if value == 'touch':
            self.circuit.contact_method.value = 0
            self.circuit.contact_ch.value = 128
        else:
            self.circuit.contact_method.value = 1
            self.circuit.contact_ch.value = 129

    def _apply_aversive_stimulus(self, value):
        IO = ['info light', 'bright light', 'air puff', 'shock']
        stimuli = self.model.paradigm.aversive_stimulus
        word = sum([2**IO.index(s) for s in value])
        self.circuit.aversive_word.value = word

class AversiveController(BaseAversiveController):

    circuits = { 'circuit': ('aversive-behavior', 'RX6') }

    parameter_map = {'lick_th': 'circuit.lick_th',
                     'requested_lick_fs': 'circuit.lick_nPer',
                     'contact_method': 'handler._apply_contact_method', 
                     'aversive_stimulus': 'handler._apply_aversive_stimulus',
                     'aversive_delay': 'circuit.aversive_del_n',
                     'aversive_duration': 'circuit.aversive_dur_n',
                     }

    @on_trait_change('fast_tick')
    def task_update_data(self):
        self.contact_pipe.send(self.circuit.contact_buf.read())

    def _apply_signal_safe(self):
        paradigm = self.model.paradigm
        self.current_safe = generate_signal(paradigm.signal, paradigm.par_safe)
        print "DEPTH", self.current_safe.env_depth
        self.circuit.int_buf.set(self.current_safe)

    @on_trait_change('fast_tick')
    def task_monitor_signal_safe(self):
        if self.circuit.int_buf.block_processed():
            samples = self.current_safe.read_block()
            self.circuit.int_buf.write(samples)
    
    def _apply_signal_remind(self):
        # The actual sequence is important.  We must finish uploading the signal
        # before we set the circuit flags to allow commencement of a trial.
        signal = self.model.paradigm.signal
        signal.set_variable(self.current_par_remind)
        self.circuit.trial_buf.set(signal)
        self.backend.set_attenuation(signal.attenuation, 'PA5')

    def _apply_signal_warn(self):
        log.debug('Apply signal warn')
        signal = self.model.paradigm.signal
        signal.set_variable(self.current_par)
        self.circuit.trial_buf.set(signal)
        self.backend.set_attenuation(signal.attenuation, 'PA5')

    def init_experiment(self, info):
        self._apply_signal_warn()
        self.circuit.contact_buf.initialize(channels=4, sf=127, src_type=np.int8,
                                            fs=self.circuit.lick_nPer.get('fs'))
        super(AversiveController, self).init_experiment(info)


class AversiveFMController(BaseAversiveController):

    circuits = { 'circuit': ('aversive-behavior-FM', 'RX6') }

    parameter_map = {'lick_th': 'circuit.lick_th',
                     'requested_lick_fs': 'circuit.lick_nPer',
                     'contact_method': 'handler._apply_contact_method', 
                     'aversive_stimulus': 'handler._apply_aversive_stimulus',
                     'aversive_delay': 'circuit.aversive_del_n',
                     'aversive_duration': 'circuit.aversive_dur_n',
                     'carrier_frequency': 'circuit.cf',
                     'modulation_frequency': 'circuit.fm',
                     'attenuation': 'handler._apply_attenuation',
                     'trial_duration': 'circuit.trial_dur_n',
                     }

    @on_trait_change('fast_tick')
    def task_update_data(self):
        self.contact_pipe.send(self.circuit.contact_buf.read())

    def _apply_signal_warn(self):
        self.circuit.depth.value = self.current_par

    def _apply_signal_remind(self):
        self.circuit.depth.value = self.current_par_remind

    def _apply_signal_safe(self):
        print self.current_safe
        if self.current_safe != 0:
            raise ValueError, 'Safe parameter must be 0!'

    def _apply_attenuation(self, value):
        self.backend.set_attenuation(value, 'PA5')

    def init_experiment(self, info):
        log.debug('init_experiment')
        self._apply_signal_warn()
        self.circuit.contact_buf.initialize(channels=4, 
                                            src_type=np.int8,
                                            sf=127,
                                            fs=self.circuit.lick_nPer.get('fs'))
        super(AversiveFMController, self).init_experiment(info)

class AversivePhysiologyController(AversiveController):

    circuits = {'circuit': ('aversive-behavior', 'RX6'),
                'circuit_physiology': ('aversive-physiology', 'RZ5'), 
               }

    circuit_physiology = Any
    ch_monitor = Range(1, 16, 1)
    
    def init_equipment(self, info):
        super(AversivePhysiologyController, self).init_equipment(info)
        self.circuit_physiology = equipment.dsp().load('aversive-physiology', 'RZ5')
        self.circuit_physiology.open('mc_sig', 'r', 
                                     src_type=np.float32, 
                                     dest_type=np.float32, 
                                     channels=17, 
                                     read='continuous',
                                     sf=1)
        self.circuit_physiology.open('triggers', 'r')
        self.circuit_physiology.start()
        
    @on_trait_change('fast_tick')
    def task_update_physiology(self):
        try:
            data = self.circuit_physiology.mc_sig.next()
            self.model.data.neural_data.send(data)
            data = self.circuit_physiology.triggers.next()
            self.model.data.neural_triggers.send(data)
        except StopIteration:
            pass

    def initialize_data(self, model):
        exp_name = 'date_' + datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
        model.exp_node = append_node(model.store_node, exp_name)
        model.data_node = append_node(model.exp_node, 'AversiveData')
        model.data = AversivePhysiologyData(contact_fs=model.paradigm.actual_lick_fs,
                                  store_node=model.data_node)
        
    def _ch_monitor_changed(self, new):
        self.circuit_physiology.ch_monitor = new

if __name__ == "__main__":
    print AversiveController().parameter_map

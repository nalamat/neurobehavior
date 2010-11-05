from .experiment_controller import ExperimentController
from cns.pipeline import int_to_TTL, deinterleave
from functools import partial
from cns.data.h5_utils import append_date_node, append_node
from cns import choice, equipment
from cns.data.h5_utils import append_node, append_date_node, \
    get_or_append_node
from cns.data.persistence import add_or_update_object
from cns.experiment.data.positive_data import PositiveData
from cns.experiment.data.positive_data import PositiveDataStage1
from cns.experiment.paradigm.positive_paradigm import PositiveParadigm
from datetime import timedelta, datetime
from enthought.pyface.api import error
from enthought.pyface.timer.api import Timer
from enthought.traits.api import Any, Instance, CInt, CFloat, Str, Float, \
    Property, HasTraits, Bool, on_trait_change, Dict, Button, Event, Int
from enthought.traits.ui.api import HGroup, spring, Item, View
import logging
import time
import numpy as np

log = logging.getLogger(__name__)

class PositiveControllerStage1(ExperimentController):

    circuits = {'circuit': ('positive-behavior-stage1', 'RX6') }
    circuit = Any
    fast_tick = Event

    parameter_map = {
            'spout_sensor': 'handler._apply_spout_sensor',
            'TTL_fs': 'circuit.TTL_nPer', }

    def init_experiment(self, info):
        super(PositiveControllerStage1, self).init_experiment(info)
        exp_node = append_date_node(self.model.store_node,
                pre='appetitive_stage1_date')
        data_node = append_node(exp_node, 'data')
        self.model.data = PositiveDataStage1(store_node=data_node)
        self.model.exp_node = exp_node
        self.circuit.TTL.initialize(src_type=np.int8, compression='decimated')
        self.circuit.DAC1a.set(self.model.paradigm.signal)

    def start_experiment(self, info):
        self.circuit.start()
        self.fast_timer = Timer(250, self.tick, 'fast')
        self.state = 'running'

    def stop_experiment(self, info):
        #self.fast_timer.stop()
        self.state = 'halted'

    pipeline = Any

    def _pipeline_default(self):
        targets = [self.model.data.spout_TTL,
                   self.model.data.override_TTL,
                   self.model.data.pump_TTL, ]
        return int_to_TTL(len(targets), deinterleave(targets))

    @on_trait_change('fast_tick')
    def monitor_circuit(self):
        self.pipeline.send(self.circuit.TTL.read().astype(np.int8))

    def _apply_spout_sensor(self, value):
        if value == 'touch':
            self.circuit.sensor.value = 0
        else:
            self.circuit.sensor.value = 2

    def log_event(self, *args, **kw):
        pass

class PositiveController(ExperimentController):
    '''
    '''

    circuits = { 'circuit': ('positive-behavior-stage3', 'RX6') }
    circuit = Any

    parameter_map = {'intertrial_duration': 'circuit.int_dur_n',
                     'response_window_delay': 'circuit.resp_del_n',
                     'response_window_duration': 'circuit.resp_dur_n',
                     'score_window_duration': 'circuit.score_dur_n', 
                     'reward_duration': 'circuit.reward_dur_n', 
                     'signal_offset_delay': 'circuit.sig_offset_del_n', 
                     'spout_sensor': 'handler._apply_spout_sensor',
                     'spout_smooth_duration': 'circuit.spout_smooth_n', 
                     'timeout_duration': 'circuit.to_dur_n', 
                     'TTL_fs': 'circuit.TTL_nPer' }
    backend = Any
    circuit = Any
    pump = Any

    fast_timer = Instance(Timer)

    # A coroutine pipeline that acquires contact data from the RX6 and sends it
    # to the TrialData object
    pipeline = Any
    completed = Bool(False)
    water_infused = Float(0)

    status = Property(Str, depends_on='state, current_trial, current_num_nogo')

    fast_tick = Event

    def init_equipment(self, info):
        super(PositiveController, self).init_equipment(info)
        self.pump = equipment.pump().Pump()

    current_trial_start_idx = Int
    current_trial_end_idx = Int

    current_trial = Int
    current_poke_dur = Float
    current_num_nogo = Int
    current_repeat_FA = Bool

    choice_poke_dur = Any
    choice_num_nogo = Any

    def init_experiment(self, info):
        super(PositiveController, self).init_experiment(info)

        # Set up storage nodes
        exp_node = append_date_node(self.model.store_node,
                                    pre='appetitive_date_')
        data_node = append_node(exp_node, 'data')
        self.model.data = PositiveData(store_node=data_node)
        self.model.exp_node = exp_node
        
        self.circuit.TTL.initialize(src_type=np.int8, compression='decimated')
        self._apply_go_signal()
        self._apply_nogo_signal()
        self.circuit.signal_dur_n.value = self.circuit.go_buf_n.value
        self.init_current(info)
        self.current_trial_start_idx = 0
        self.current_trial_end_idx = 0

    def start_experiment(self, info):
        self.fast_timer = Timer(250, self.tick, 'fast')
        self.model.data.start_time = datetime.now()
        self.state = 'running'
        self.circuit.start()
        self.circuit.trigger(1)

    def stop_experiment(self, info=None):
        self.state = 'halted'
        self.fast_timer.stop()
        self.circuit.stop()
        self.pending_changes = {}
        self.old_values = {}

        self.model.data.stop_time = datetime.now()
        #add_or_update_object(self.pump, self.model.exp_node, 'Pump')
        add_or_update_object(self.model.paradigm, self.model.exp_node, 'paradigm')
        add_or_update_object(self.model.data, self.model.exp_node, 'data')

    #===========================================================================
    # Tasks driven by the slow and fast timers
    #===========================================================================
    #@on_trait_change('fast_tick')
    #def task_update_pump(self):
    #    self.water_infused = self.pump.infused

    def _get_status(self):
        if self.state == 'disconnected':
            return 'Cannot connect to equipment'
        elif self.state == 'halted':
            return 'System is halted'

        base = 'Next trial: '
        if self.current_trial <= self.current_num_nogo:
            return base + 'NOGO %d of %d' % (self.current_trial,
                    self.current_num_nogo)
        else:
            return base + 'GO'
            
    def _pipeline_default(self):
        targets = [self.model.data.poke_TTL,
                   self.model.data.spout_TTL,
                   self.model.data.signal_TTL,
                   self.model.data.score_TTL,
                   self.model.data.reward_TTL,
                   self.model.data.response_TTL,
                   ]
        return int_to_TTL(len(targets), deinterleave(targets))

    @on_trait_change('fast_tick')
    def monitor_circuit(self):
        self.pipeline.send(self.circuit.TTL.read().astype(np.int8))

        if self.circuit.trial_end_idx.value > self.current_trial_end_idx:
            # Trial is over.  Process new data and set up for next trial.
            ts_start = self.circuit.trial_start_ts.value
            ts_end = self.circuit.trial_end_ts.value

            # In this context, current_trial reflects the trial that just
            # occured
            if self.current_trial == self.current_num_nogo + 1:
                last_ttype = 'GO'
            else:
                last_ttype = 'NOGO'
            self.model.data.log_trial(ts_start, ts_end, last_ttype)

            if last_ttype == 'NOGO' and self.current_repeat_FA:
                if self.model.data.trial_log[-1][3] == 'SPOUT':
                    log.debug("FA detected, adding a NOGO trial")
                    self.current_num_nogo += 1

            # From now on, current_trial indicates the next trial that will
            # occur
            self.current_trial += 1

            if self.current_trial == self.current_num_nogo + 2:
                self.current_num_nogo = self.choice_num_nogo()
                self.current_trial = 1
            if self.current_trial == self.current_num_nogo + 1:
                self.circuit.trigger(2)

            self.current_trial_end_idx += 1
            self.current_poke_dur = self.choice_poke_dur()
            self.circuit.poke_dur_n.set(self.current_poke_dur, 's')
            self.circuit.trigger(1)

    def init_current(self, info=None):
        # Refresh selectors
        lb = self.model.paradigm.poke_duration_lb
        ub = self.model.paradigm.poke_duration_ub
        self.choice_poke_dur = partial(np.random.uniform, lb, ub)

        lb = self.model.paradigm.min_nogo
        ub = self.model.paradigm.max_nogo
        self.choice_num_nogo = partial(np.random.randint, lb, ub+1)

        # Refresh experiment state
        self.current_trial = 1
        self.current_num_nogo = self.choice_num_nogo()
        self.current_poke_dur = self.choice_poke_dur()
        self.circuit.poke_dur_n.set(self.current_poke_dur, 's')

        self.current_repeat_FA = self.model.paradigm.repeat_FA

        if self.current_trial == self.current_num_nogo + 1:
            self.circuit.trigger(2)

    ############################################################################
    # Code to apply parameter changes
    ############################################################################
    def _reset_current(self, value):
        self.init_current()

    _apply_poke_duration_lb = _reset_current
    _apply_poke_duration_ub = _reset_current
    _apply_min_nogo = _reset_current
    _apply_max_nogo = _reset_current
    _apply_repeat_FA = _reset_current

    def _apply_go_signal(self):
        signal = self.model.paradigm.go_signal
        self.circuit.go_buf.set(signal)
        self.backend.set_attenuation(signal.attenuation, 'PA5')

    def _apply_nogo_signal(self):
        signal = self.model.paradigm.nogo_signal
        self.circuit.nogo_buf.set(signal)
        self.backend.set_attenuation(signal.attenuation, 'PA5')

    def _apply_spout_sensor(self, value):
        if value == 'touch':
            self.circuit.contact_method.value = 0
        else:
            self.circuit.contact_method.value = 2

    def log_event(self, ts, name, value):
        pass

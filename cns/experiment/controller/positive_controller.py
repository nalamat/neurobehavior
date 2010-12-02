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
from enthought.traits.api import Any, Instance, CInt, CFloat, Str, Float, \
    Property, HasTraits, Bool, on_trait_change, Dict, Button, Event, Int
from enthought.traits.ui.api import HGroup, spring, Item, View
import logging
import time
import numpy as np

from .pump_controller_mixin import PumpControllerMixin

log = logging.getLogger(__name__)

class PositiveControllerStage1(ExperimentController, PumpControllerMixin):

    circuits = {'circuit': ('positive-behavior-stage1', 'RX6') }
    circuit = Any

    parameter_map = {
            'spout_sensor': 'handler._apply_spout_sensor',
            'TTL_fs': 'circuit.TTL_nPer', 
            'syringe_diameter': 'handler._apply_syringe_diameter',
            'pump_rate': 'handler._apply_pump_rate', }

    pipeline = Any

    def init_experiment(self, info):
        super(PositiveControllerStage1, self).init_experiment(info)
        exp_node = append_date_node(self.model.store_node,
                                    pre='appetitive_stage1_date_')
        data_node = append_node(exp_node, 'data')
        self.model.data = PositiveDataStage1(store_node=data_node)
        self.model.exp_node = exp_node
        self.circuit.TTL.initialize(src_type=np.int8)
        self.circuit.DAC1a.set(self.model.paradigm.signal)

        #self.pump.diameter = self.model.paradigm.syringe_diameter
        targets = [self.model.data.spout_TTL,
                   self.model.data.override_TTL,
                   self.model.data.pump_TTL, ]
        self.pipeline = int_to_TTL(len(targets), deinterleave(targets))

    def start_experiment(self, info):
        self.model.data.start_time = datetime.now()
        self.circuit.start()
        self.circuit.trigger(1)
        self.state = 'running'

    def resume(self, info):
        self.circuit.trigger(1)
        self.state = 'running'

    def pause(self, info):
        self.circuit.trigger(2)
        self.state = 'paused'

    def stop_experiment(self, info):
        self.circuit.stop()
        self.state = 'halted'
        self.model.data.stop_time = datetime.now()
        #add_or_update_object(self.pump, self.model.exp_node, 'Pump')
        add_or_update_object(self.model.paradigm, self.model.exp_node, 'paradigm')
        add_or_update_object(self.model.data, self.model.exp_node, 'data')

    def tick(self):
        data = self.circuit.TTL.read().astype(np.int8)
        self.pipeline.send(data)

    def _apply_spout_sensor(self, value):
        if value == 'touch':
            self.circuit.sensor.value = 0
        else:
            self.circuit.sensor.value = 2

    def log_event(self, *args, **kw):
        pass

class PositiveController(ExperimentController, PumpControllerMixin):

    circuits = { 'circuit': ('positive-behavior-stage3', 'RX6') }
    circuit = Any

    parameter_map = {'intertrial_duration': 'circuit.int_dur_n',
                     'response_window_delay': 'circuit.resp_del_n',
                     'response_window_duration': 'circuit.resp_dur_n',
                     'score_window_duration': 'circuit.score_dur_n', 
                     'reward_duration': 'circuit.reward_dur_n', 
                     'signal_offset_delay': 'circuit.sig_offset_del_n', 
                     'timeout_duration': 'circuit.to_dur_n', 
                     'TTL_fs': 'circuit.TTL_nPer',
                     'syringe_diameter': 'handler._apply_syringe_diameter',
                     'pump_rate': 'handler._apply_pump_rate', }
    backend = Any
    circuit = Any

    # A coroutine pipeline that acquires contact data from the RX6 and sends it
    # to the TrialData object
    pipeline = Any
    completed = Bool(False)
    water_infused = Float(0)

    status = Property(Str, depends_on='state, current_trial, current_num_nogo')

    current_loop = Int

    #current_trial_start_ts = Int
    current_trial_end_ts = Int

    current_trial = Int
    current_poke_dur = Float

    current_num_nogo = Int
    current_repeat_FA = Bool
    current_parameter = Any
    current_nogo_parameter = Any

    choice_poke_dur = Any
    choice_num_nogo = Any
    choice_parameter = Any

    def init_current(self, info=None):
        # Refresh selectors
        lb = self.model.paradigm.poke_duration_lb
        ub = self.model.paradigm.poke_duration_ub
        self.choice_poke_dur = partial(np.random.uniform, lb, ub)

        lb = self.model.paradigm.min_nogo
        ub = self.model.paradigm.max_nogo
        self.choice_num_nogo = partial(np.random.randint, lb, ub+1)

        selector = self.model.paradigm.parameter_order_
        import copy
        sequence = copy.deepcopy(self.model.paradigm.parameters)
        self.choice_parameter = selector(sequence)

        # Refresh experiment state
        self.current_trial = 1
        self.current_parameter = self.choice_parameter.next()
        self.current_num_nogo = self.choice_num_nogo()
        self.current_poke_dur = self.choice_poke_dur()
        self.circuit.poke_dur_n.set(self.current_poke_dur, 's')

        # Make copies of the parameters that can be changed during the
        # experiment.
        self.current_repeat_FA = self.model.paradigm.repeat_FA
        self.current_nogo_parameter = self.model.paradigm.nogo_parameter

        if self.current_trial == self.current_num_nogo + 1:
            self.circuit.trigger(2)

    def init_experiment(self, info):
        super(PositiveController, self).init_experiment(info)
        self.init_current(info)

        # Set up storage nodes
        exp_node = append_date_node(self.model.store_node,
                                    pre='appetitive_date_')
        data_node = append_node(exp_node, 'data')
        self.model.data = PositiveData(store_node=data_node)
        self.model.exp_node = exp_node
        
        # Configure circuit
        self.circuit.TTL.initialize(src_type=np.int8)
        self._apply_go_signal()
        self._apply_nogo_signal()
        self.circuit.signal_dur_n.value = self.circuit.go_buf_n.value
        #self.current_trial_start_idx = 0
        self.current_trial_end_ts = self.circuit.trial_end_ts.value
        print 'TRIAL_TS_END', self.current_trial_end_ts

        targets = [
                self.model.data.poke_TTL,
                self.model.data.spout_TTL,
                self.model.data.signal_TTL,
                self.model.data.score_TTL,
                self.model.data.reward_TTL,
                self.model.data.response_TTL,
                   ]
        self.pipeline = int_to_TTL(len(targets), deinterleave(targets))

    def start_experiment(self, info):
        self.state = 'running'
        self.current_loop = 0
        self.model.data.start_time = datetime.now()
        self.circuit.start()
        print self.circuit.trial_end_ts.value
        self.circuit.trigger(1)
        print self.circuit.trial_end_ts.value

    def stop_experiment(self, info=None):
        self.state = 'halted'
        self.circuit.stop()
        self.model.data.stop_time = datetime.now()
        add_or_update_object(self.model.paradigm, self.model.exp_node, 'paradigm')
        add_or_update_object(self.model.data, self.model.exp_node, 'data')

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
            
    ############################################################################
    # Master controller
    ############################################################################
    def tick(self):
        self.current_loop += 1

        # Don't be silly.  We don't need to query the pump on *every* tick (it's
        # actually quite a slow operation).
        if (self.current_loop % 5) == 0:
            self.water_infused = self.pump.infused
            # update status here

        print self.circuit.trial_end_ts.value
        if self.circuit.trial_end_ts.value > self.current_trial_end_ts:
            # Trial is over.  Process new data and set up for next trial.
            ts_start = self.circuit.trial_start_ts.value
            ts_end = self.circuit.trial_end_ts.value
            self.current_trial_end_ts = ts_end

            # Read the TTL data after we read ts_start and ts_end, but before we
            # score the data.  This ensures that we have the most up-to-date TTL
            # data for the scoring.
            self.pipeline.send(self.circuit.TTL.read().astype(np.int8))

            # In this context, current_trial reflects the trial that just
            # occured
            log.debug('Current trial: %d, NOGO count: %d', self.current_trial,
                      self.current_num_nogo)
            if self.current_trial == self.current_num_nogo + 1:
                last_ttype = 'GO'
            else:
                last_ttype = 'NOGO'

            # Sometimes it takes a ms for the requisite contact data to come
            # through due to downsampling.  Keep trying until the data is
            # available.
            while True:
                try:
                    self.model.data.log_trial(ts_start, ts_end, last_ttype)
                    break
                except IndexError, e:
                    log.exception(e)
                    self.pipeline.send(self.circuit.TTL.read().astype(np.int8))

            # Increment num_nogo
            if last_ttype == 'NOGO' and self.current_repeat_FA:
                if self.model.data.trial_log[-1][3] == 'SPOUT':
                    log.debug("FA detected, adding a NOGO trial")
                    self.current_num_nogo += 1

            if self.current_trial == self.current_num_nogo + 1:
                # GO was just presented.  Set up for next block of trials.
                self.current_num_nogo = self.choice_num_nogo()
                self.current_parameter = self.choice_parameter.next()
                self.current_trial = 1
            else:
                self.current_trial += 1

            # Current trial is now the "next" trial to be presented.  Prepare
            # circuit accordingly.
            if self.current_trial == self.current_num_nogo + 1:
                # Next trial should be a GO.  Prepare circuit.
                self.circuit.GO.value = 1
                #self.circuit.trigger(2)
                self._apply_go_signal()
            else:
                # Refresh NOGO (important for non-frozen noise)
                self.circuit.GO.value = 0
                self._apply_nogo_signal()
                pass

            #self.current_parameter = self.choice_parameter.next()
            #self.current_trial_end_idx += 1
            self.current_poke_dur = self.choice_poke_dur()
            self.circuit.poke_dur_n.set(self.current_poke_dur, 's')
            self.circuit.trigger(1)

        else:
            self.pipeline.send(self.circuit.TTL.read().astype(np.int8))

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
    _apply_parameter_order = _reset_current
    _apply_parameters = _reset_current

    def _apply_go_signal(self):
        print self.current_parameter
        signal = self.model.paradigm.signal
        current = self.current_parameter
        signal.set_variable(current.parameter)
        self.circuit.go_buf.set(signal)
        self.backend.set_attenuation(signal.attenuation, 'PA5')
        self.pump.rate = current.reward_rate
        self.circuit.reward_dur_n.set(current.reward_duration, 's')

    def _apply_nogo_signal(self):
        signal = self.model.paradigm.signal
        signal.set_variable(self.current_nogo_parameter)
        self.circuit.nogo_buf.set(signal)
        self.backend.set_attenuation(signal.attenuation, 'PA5')

    _apply_parameters_items = _reset_current
    _apply_reward_rate = _reset_current
    _apply_reward_duration = _reset_current

    def log_event(self, ts, name, value):
        pass

from functools import partial

from enthought.traits.api import Str, Property, Float, on_trait_change
from tdt import DSPCircuit
from pump_controller_mixin import PumpControllerMixin
from abstract_experiment_controller import AbstractExperimentController
from cns.pipeline import deinterleave_bits
from cns.data.h5_utils import append_date_node, append_node
from cns import choice
from cns.data.persistence import add_or_update_object
from positive_data import PositiveData
from positive_paradigm import PositiveParadigm

import numpy as np


import logging
log = logging.getLogger(__name__)

class PositiveController(AbstractExperimentController, PumpControllerMixin):

    water_infused = Float(0)
    status = Property(Str, depends_on='state, current_trial, current_num_nogo')

    def init_current(self, info=None):
        # Update random selector for poke duration using new bounds
        lb = self.model.paradigm.poke_duration_lb
        ub = self.model.paradigm.poke_duration_ub
        self.choice_poke_dur = partial(np.random.uniform, lb, ub)

        # Update random selector for trial number
        lb = self.model.paradigm.min_nogo
        ub = self.model.paradigm.max_nogo
        self.choice_num_nogo = partial(np.random.randint, lb, ub+1)

        # Deepcopy because we need to ensure that it does not update while we
        # are making changes
        selector = self.model.paradigm.parameter_order_
        import copy
        sequence = copy.deepcopy(self.model.paradigm.parameters)
        self.choice_parameter = selector(sequence)

        # Refresh experiment state
        self.current_trial = 1
        self.current_setting_go = self.choice_parameter.next()
        self.current_num_nogo = self.choice_num_nogo()
        self.current_poke_dur = self.choice_poke_dur()
        self.set_poke_duration(self.current_poke_dur)

        # Make copies of the parameters that can be changed during the
        # experiment.
        self.current_repeat_FA = self.model.paradigm.repeat_FA
        self.current_nogo_parameter = self.model.paradigm.nogo_parameter
        self.current_trial_dur = self.model.paradigm.trial_duration

        log.debug("Initialized current settigns")

    def start_experiment(self, info):
        # Load interface for the experiment
        self.init_pump()

        self.iface_behavior = DSPCircuit('components/positive-behavior', 'RZ6')
        self.buffer_signal = self.iface_behavior.get_buffer('speaker')
        self.buffer_TTL = self.iface_behavior.get_buffer('TTL', src_type=np.int8,
                dest_type=np.int8, block_size=24)

        #self.buffer_trial_start_TS = self.iface_behavior.get_buffer('trial/',
                #src_type=np.int32, block_size=1)
        #self.buffer_trial_end_TS = self.iface_behavior.get_buffer('trial\\',
                #src_type=np.int32, block_size=1)
        self.buffer_to_start_TS = self.iface_behavior.get_buffer('TO/',
                src_type=np.int32, block_size=1)
        self.buffer_to_end_TS = self.iface_behavior.get_buffer('TO\\',
                src_type=np.int32, block_size=1)

        paradigm = self.model.paradigm

        self.init_current(info)

        # Configure the RPvds circuit
        self.set_intertrial_duration(paradigm.intertrial_duration)
        self.set_reaction_window_delay(paradigm.reaction_window_delay)
        self.set_reaction_window_duration(paradigm.reaction_window_duration)
        self.set_response_window_duration(paradigm.response_window_duration)
        self.set_reward_duration(paradigm.reward_duration)
        self.set_signal_offset_delay(paradigm.signal_offset_delay)
        self.set_timeout_duration(paradigm.timeout_duration)
        self.set_attenuation(paradigm.attenuation)
        self.set_timeout_trigger(paradigm.timeout_trigger)

        # Set up storage nodes
        exp_node = append_date_node(self.model.store_node,
                                    pre='appetitive_date_')
        data_node = append_node(exp_node, 'data')
        self.model.data = PositiveData(store_node=data_node)

        self.model.data.trial_start_timestamp.fs = self.buffer_TTL.fs
        self.model.data.trial_end_timestamp.fs = self.buffer_TTL.fs
        self.model.data.timeout_start_timestamp.fs = self.buffer_TTL.fs
        self.model.data.timeout_end_timestamp.fs = self.buffer_TTL.fs
        self.model.data.spout_TTL.fs = self.buffer_TTL.fs
        self.model.data.poke_TTL.fs = self.buffer_TTL.fs
        self.model.data.signal_TTL.fs = self.buffer_TTL.fs
        self.model.data.reaction_TTL.fs = self.buffer_TTL.fs
        self.model.data.response_TTL.fs = self.buffer_TTL.fs
        self.model.data.reward_TTL.fs = self.buffer_TTL.fs

        self.model.exp_node = exp_node

        targets = [self.model.data.poke_TTL, self.model.data.spout_TTL,
                   self.model.data.reaction_TTL, self.model.data.signal_TTL,
                   self.model.data.response_TTL, self.model.data.reward_TTL, ]

        self.pipeline_contact = deinterleave_bits(targets)
        
        # Configure circuit
        self.current_trial_end_ts = self.get_trial_end_ts()

        self.state = 'running'
        self.iface_behavior.start()
        self.iface_behavior.trigger('A', 'high')
        self.trigger_next()

    def stop_experiment(self, info=None):
        self.state = 'halted'
        self.iface_behavior.trigger('A', 'low')
        self.iface_behavior.stop()
        add_or_update_object(self.model.paradigm, self.model.exp_node, 'paradigm')
        add_or_update_object(self.model.data, self.model.exp_node, 'data')

    def _get_status(self):
        if self.state == 'disconnected':
            return 'Cannot connect to equipment'
        elif self.state == 'halted':
            return 'System is halted'

        if self.current_trial <= self.current_num_nogo:
            return 'NOGO %d of %d' % (self.current_trial,
                    self.current_num_nogo)
        else:
            return 'GO'
            
    ############################################################################
    # Master controller
    ############################################################################
    def tick_slow(self):
        log.debug("TICK SLOW")
        ts = self.get_ts()
        seconds = int(ts/self.iface_behavior.fs)
        self.monitor_pump()
        self.model.data.timeout_start_timestamp.send(self.buffer_to_start_TS.read())
        self.model.data.timeout_end_timestamp.send(self.buffer_to_end_TS.read())
        log.debug("COMPLETE")

    def tick_fast(self):
        log.debug('TICK')
        ts_end = self.get_trial_end_ts()
        self.pipeline_contact.send(self.buffer_TTL.read())
        if ts_end > self.current_trial_end_ts:
            # Trial is over.  Process new data and set up for next trial.
            self.current_trial_end_ts = ts_end
            ts_start = self.get_trial_start_ts()

            # Read the TTL data after we read ts_start and ts_end, but before we
            # score the data.  This ensures that we have the most up-to-date TTL
            # data for the scoring.
            #self.pipeline.send(self.project.behavior.TTL.read().astype(np.int8))

            # In this context, current_trial reflects the trial that just
            # occured
            if self.current_trial == self.current_num_nogo + 1:
                last_ttype = 'GO'
            else:
                last_ttype = 'NOGO'
            parameter = self.current_setting_go.parameter

            self.model.data.log_trial(ts_start, ts_end, last_ttype, parameter)

            # Increment num_nogo
            if last_ttype == 'NOGO' and self.current_repeat_FA:
                #if self.model.data.trial_log[-1][3] == 'spout':
                if self.model.data.resp_seq[-1] == 'spout':
                    log.debug("FA detected, adding a NOGO trial")
                    self.current_num_nogo += 1

            log.debug('Last trial: %d, NOGO count: %d', self.current_trial,
                      self.current_num_nogo)

            if self.current_trial == self.current_num_nogo + 1:
                # GO was just presented.  Set up for next block of trials.
                self.current_num_nogo = self.choice_num_nogo()
                self.current_setting_go = self.choice_parameter.next()
                self.current_poke_dur = self.choice_poke_dur()
                self.current_trial = 1
            else:
                self.current_trial += 1

            log.debug('Next trial: %d, NOGO count: %d', self.current_trial,
                      self.current_num_nogo)

            self.trigger_next()
            log.debug("returned to loop")

    ############################################################################
    # Code to apply parameter changes.  This is backend-specific.  If you want
    # to implement a new backend, you would subclass this and override the
    # appropriate set_* methods.
    ############################################################################

    @on_trait_change('model.paradigm.parameters.+')
    def queue_parameter_change(self, object, name, old, new):
        self.queue_change(self.model.paradigm, 'parameters',
                self.current_parameters, self.model.paradigm.parameters)


    set_poke_duration_lb         = AbstractExperimentController.reset_current
    set_poke_duration_ub         = AbstractExperimentController.reset_current
    set_min_nogo                 = AbstractExperimentController.reset_current
    set_max_nogo                 = AbstractExperimentController.reset_current
    set_repeat_FA                = AbstractExperimentController.reset_current
    set_parameter_order          = AbstractExperimentController.reset_current
    set_parameters               = AbstractExperimentController.reset_current
    set_parameters_items         = AbstractExperimentController.reset_current

    set_reward_rate              = AbstractExperimentController.reset_current
    set_reward_duration          = AbstractExperimentController.reset_current

    def set_repeat_FA(self, value):
        self.current_repeat_FA = value

    def set_intertrial_duration(self, value):
        self.iface_behavior.cset_tag('int_dur_n', value, 's', 'n')

    def set_reaction_window_delay(self, value):
        self.iface_behavior.cset_tag('react_del_n', value, 's', 'n')
        if self.iface_behavior.get_tag('react_del_n') == 0:
            self.iface_behavior.set_tag('react_del_n', 1)

    def set_reaction_window_duration(self, value):
        delay = self.model.paradigm.reaction_window_delay
        self.iface_behavior.cset_tag('react_end_n', delay+value, 's', 'n')

    def set_response_window_duration(self, value):
        self.iface_behavior.cset_tag('resp_dur_n', value, 's', 'n')

    def set_reward_duration(self, value):
        self.iface_behavior.cset_tag('reward_dur_n', value, 's', 'n')

    def set_signal_offset_delay(self, value):
        self.iface_behavior.cset_tag('sig_offset_del_n', value, 's', 'n')

    def set_timeout_duration(self, value):
        self.iface_behavior.cset_tag('to_dur_n', value, 's', 'n')

    def set_poke_duration(self, value):
        self.iface_behavior.cset_tag('poke_dur_n', value, 's', 'n')

    def get_ts(self, req_unit=None):
        return self.iface_behavior.get_tag('zTime')

    def get_trial_end_ts(self):
        return self.iface_behavior.get_tag('trial\\')

    def get_trial_start_ts(self):
        return self.iface_behavior.get_tag('trial/')

    def set_attenuation(self, value):
        self.iface_behavior.set_tag('att_A', value)

    def set_timeout_trigger(self, value):
        flag = 0 if value == 'FA only' else 1
        self.iface_behavior.set_tag('to_type', flag)

    def trigger_next(self):
        signal = self.model.paradigm.signal

        if self.current_trial == self.current_num_nogo + 1:
            par = self.current_setting_go.parameter
            self.iface_behavior.set_tag('go?', 1)
        else:
            par = self.current_nogo_parameter
            self.iface_behavior.set_tag('go?', 0)

        signal.block.set_parameter(signal.variable, par)
        waveform = signal.block.realize(self.iface_behavior.fs,
                                        self.current_trial_dur)
        self.buffer_signal.set(waveform)
        self.iface_behavior.set_tag('signal_dur_n', len(waveform))
        self.set_poke_duration(self.current_poke_dur)
        self.set_reward_duration(self.current_setting_go.reward_duration)
        self.iface_pump.rate = self.current_setting_go.reward_rate
        log.debug("Uploaded signal with par %f", par)
        self.iface_behavior.trigger(1)
        log.debug("Trigger sent")

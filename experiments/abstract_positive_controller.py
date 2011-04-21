from functools import partial

from enthought.traits.api import Str, Property, Float, on_trait_change, \
        Instance, Any
from enthought.traits.ui.api import View, Item, HGroup, spring
from pump_controller_mixin import PumpControllerMixin
from abstract_experiment_controller import AbstractExperimentController
from abstract_experiment_controller import ExperimentToolBar
from cns.pipeline import deinterleave_bits
from cns import choice
from cns.data.persistence import add_or_update_object
from positive_data import PositiveData
from copy import deepcopy

from cns import RCX_ROOT
from os.path import join

import numpy as np


import logging
log = logging.getLogger(__name__)

class PositiveExperimentToolBar(ExperimentToolBar):
    
    traits_view = View(
            HGroup(Item('apply',
                        enabled_when="object.handler.pending_changes<>{}"),
                   Item('revert',
                        enabled_when="object.handler.pending_changes<>{}",),
                   Item('start',
                        enabled_when="object.handler.state=='halted'",),
                   '_',
                   Item('remind',
                        enabled_when="object.handler.state=='running'",),
                   Item('stop',
                        enabled_when="object.handler.state in " +\
                                     "['running', 'paused', 'manual']",),
                   spring,
                   springy=True,
                   show_labels=False,
                   ),
            kind='subpanel',
            )

class AbstractPositiveController(AbstractExperimentController,
        PumpControllerMixin):

    # Override default implementation of toolbar used by AbstractExperiment
    toolbar = Instance(PositiveExperimentToolBar, (), toolbar=True)

    status = Property(Str, depends_on=['state', 'current_trial',
        'current_num_nogo', 'current_setting_go'])

    @on_trait_change('model.data.parameters')
    def update_adapter(self, value):
        self.model.trial_log_adapter.parameters = value
        self.model.par_info_adapter.parameters = value

    def setup_experiment(self, info):
        circuit = join(RCX_ROOT, 'positive-behavior-v2')
        self.iface_behavior = self.process.load_circuit(circuit, 'RZ6')

        # primary speaker
        self.buffer_out1 = self.iface_behavior.get_buffer('out1', 'w')
        # secondary speaker
        self.buffer_out2 = self.iface_behavior.get_buffer('out2', 'w')
        self.buffer_TTL1 = self.iface_behavior.get_buffer('TTL', 'r',
                src_type=np.int8, dest_type=np.int8, block_size=24)
        self.buffer_TTL2 = self.iface_behavior.get_buffer('TTL2', 'r',
                src_type=np.int8, dest_type=np.int8, block_size=24)

        self.model.data.spout_TTL.fs = self.buffer_TTL1.fs
        self.model.data.poke_TTL.fs = self.buffer_TTL1.fs
        self.model.data.signal_TTL.fs = self.buffer_TTL1.fs
        self.model.data.reaction_TTL.fs = self.buffer_TTL1.fs
        self.model.data.response_TTL.fs = self.buffer_TTL1.fs
        self.model.data.reward_TTL.fs = self.buffer_TTL1.fs
        self.model.data.TO_TTL.fs = self.buffer_TTL2.fs
        self.model.data.TO_safe_TTL.fs = self.buffer_TTL2.fs

        targets1 = [self.model.data.poke_TTL, self.model.data.spout_TTL,
                    self.model.data.reaction_TTL, self.model.data.signal_TTL,
                    self.model.data.response_TTL, self.model.data.reward_TTL, ]
        targets2 = [self.model.data.TO_safe_TTL, self.model.data.TO_TTL, ]

        self.pipeline_TTL1 = deinterleave_bits(targets1)
        self.pipeline_TTL2 = deinterleave_bits(targets2)

    def start_experiment(self, info):
        self.init_context()
        self.update_context()

        self.iface_pump.set_trigger(start='rising', stop=None)
        self.iface_pump.set_direction('infuse')

        # Grab the current value of the timestamp from the circuit when it is
        # first loaded
        self.current_trial_end_ts = self.get_trial_end_ts()
        self.current_poke_end_ts = self.get_poke_end_ts()

        self.state = 'running'
        self.trigger_next()
        self.iface_behavior.trigger('A', 'high')

        # Add tasks to the queue
        self.tasks.append((self.monitor_behavior, 1))
        self.tasks.append((self.monitor_pump, 5))

    def _get_status(self):
        if self.state == 'disconnected':
            return 'Cannot connect to equipment'
        elif self.state == 'halted':
            return 'System is halted'

        if self.current_trial <= self.current_num_nogo:
            result= 'NOGO %d of %d' % (self.current_trial,
                                       self.current_num_nogo)
        else:
            result = 'GO'
        return result

    def acquire_trial_lock(self):
        # Pause circuit and see if trial is running.  If trial is already
        # running, it's too late and a lock cannot be acquired.  If trial is not
        # running, changes can be made.  A lock is returned (note this is not
        # thread-safe).
        log.debug("Setting pause state to True")
        self.set_pause_state(True)
        if self.get_trial_running():
            log.debug("Trial is running, let's try later")
            self.set_pause_state(False) 
            return False
        else:
            return True

    def release_trial_lock(self):
        log.debug("Releasing trial lock")
        self.set_pause_state(False)

    def remind(self, info=None):
        if self.acquire_trial_lock():
            self.current_trial = 1
            self.current_num_nogo = 0
            self.trigger_next()
            self.current_go_requested = False
            self.release_trial_lock()
        else:
            self.current_go_requested = True

    ############################################################################
    # Master controller
    ############################################################################
    def update_reward_settings(self, wait_time):
        # By default we do nothing
        return
    
    def monitor_behavior(self):
        ts_end = self.get_trial_end_ts()
        self.pipeline_TTL1.send(self.buffer_TTL1.read())
        self.pipeline_TTL2.send(self.buffer_TTL2.read())

        ts_poke_end = self.get_poke_end_ts()
        if ts_poke_end > self.current_poke_end_ts:
            # If poke_end has changed, we know that the subject has withdrawn
            # from the nose poke during a trial.  
            self.current_poke_end_ts = ts_poke_end
            ts_start = self.get_trial_start_ts()

            # dt is the time, in seconds, the subject took to withdraw from the
            # nose-poke relative to the beginning of the trial.  Since ts_start
            # and ts_poke_end are stored in multiples of the contact sampling
            # frequency, we can convert the timestaps to seconds by dividing by
            # the contact sampling frequency (stored in self.buffer_TTL1.fs)
            dt = (ts_poke_end-ts_start) / self.buffer_TTL1.fs
            wait_time = dt-self.current_reaction_window_delay
            self.update_reward_settings(wait_time)

        if ts_end > self.current_trial_end_ts:
            # Trial is over.  Process new data and set up for next trial.
            self.current_trial_end_ts = ts_end
            ts_start = self.get_trial_start_ts()

            # In this context, current_trial reflects the trial that just
            # occured
            last_ttype = 'GO' if self.is_go() else 'NOGO'
            self.log_trial(ts_start, ts_end, last_ttype)

            # Increment num_nogo
            if last_ttype == 'NOGO' and self.current_repeat_FA:
                if self.model.data.resp_seq[-1] == 'spout':
                    log.debug("FA detected, adding a NOGO trial")
                    self.current_num_nogo += 1

            log.debug('Last trial: %d, NOGO count: %d', self.current_trial,
                      self.current_num_nogo)

            if self.is_go():
                # GO was just presented.  Set up for next block of trials.
                self.current_setting_go = self.choice_parameter.next()
                self.update_context(self.current_setting_go.parameter_dict())
                self.current_trial = 1
            else:
                self.current_trial += 1

            if self.current_go_requested:
                self.remind()

            log.debug('Next trial: %d, NOGO count: %d', self.current_trial,
                      self.current_num_nogo)
            self.trigger_next()

    def is_go(self):
        return self.current_trial == self.current_num_nogo + 1

    ############################################################################
    # Code to apply parameter changes.  This is backend-specific.  If you want
    # to implement a new backend, you would subclass this and override the
    # appropriate set_* methods.
    ############################################################################

    @on_trait_change('model.paradigm.parameters.+')
    def queue_parameter_change(self, object, name, old, new):
        self.queue_change(self.model.paradigm, 'parameters',
                self.current_parameters, self.model.paradigm.parameters)

    def set_parameters(self, value):
        self.current_go_parameters = deepcopy(value)
        self.reset_sequence()

    def set_parameter_order(self, value):
        self.current_order = self.model.paradigm.parameter_order_
        self.reset_sequence()

    def reset_sequence(self):
        print 'resetting sequence'
        order = self.current_order
        parameters = self.current_go_parameters
        if order is not None and parameters is not None:
            self.choice_parameter = order(parameters)
            # Refresh experiment state
            if self.current_trial is None:
                self.current_trial = 1
                self.current_setting_go = self.choice_parameter.next()

    def set_poke_duration(self, value):
        # Save requested value for parameter as an attribute because we need
        # this value so we can randomly select a number between the lb and ub
        self.current_poke_duration = value

    def set_num_nogo(self, value):
        self.current_num_nogo = value

    def set_repeat_FA(self, value):
        self.current_repeat_FA = value

    def set_intertrial_duration(self, value):
        self.iface_behavior.cset_tag('int_dur_n', value, 's', 'n')

    def set_reaction_window_delay(self, value):
        self.iface_behavior.cset_tag('react_del_n', value, 's', 'n')
        # Check to see if the conversion of s to n resulted in a value of 0.
        # If so, set the delay to 1 sample (0 means that the reaction window
        # never triggers due to the nature of the RPvds component)
        if self.iface_behavior.get_tag('react_del_n') < 2:
            self.iface_behavior.set_tag('react_del_n', 2)
        self.current_reaction_window_delay = value

    def set_reaction_window_duration(self, value):
        delay = self.current_context['reaction_window_delay']
        self.iface_behavior.cset_tag('react_end_n', delay+value, 's', 'n')

    def set_response_window_duration(self, value):
        self.iface_behavior.cset_tag('resp_dur_n', value, 's', 'n')

    def set_signal_offset_delay(self, value):
        self.iface_behavior.cset_tag('sig_offset_del_n', value, 's', 'n')

    def set_poke_duration(self, value):
        self.iface_behavior.cset_tag('poke_dur_n', value, 's', 'n')

    def get_ts(self, req_unit=None):
        return self.iface_behavior.get_tag('zTime')

    def get_poke_end_ts(self):
        return self.iface_behavior.get_tag('poke\\')

    def get_trial_end_ts(self):
        return self.iface_behavior.get_tag('trial\\')

    def get_trial_start_ts(self):
        return self.iface_behavior.get_tag('trial/')

    def set_attenuation(self, value):
        self.current_attenuation = value

    def set_timeout_grace_period(self, value):
        pass

    def set_timeout_trigger(self, value):
        flag = 0 if value == 'FA only' else 1
        self.iface_behavior.set_tag('to_type', flag)

    def set_timeout_duration(self, value):
        self.iface_behavior.cset_tag('to_dur_n', value, 's', 'n')

    def get_trial_running(self):
        return self.iface_behavior.get_tag('trial_running')

    def set_pause_state(self, value):
        self.iface_behavior.set_tag('pause_state', value)

    def set_nogo(self, value):
        self.current_nogo = deepcopy(value)

    def set_reward_volume(self, value):
        self.set_pump_volume(value)

    def set_primary_attenuation(self, value):
        self.current_primary_attenuation = value
        self.iface_behavior.set_tag('att1', value)

    def set_secondary_attenuation(self, value):
        self.current_secondary_attenuation = value
        self.iface_behavior.set_tag('att2', value)

    def set_waveform(self, speaker, signal):
        silence = np.zeros(len(signal))
        if speaker == 'primary':
            self.buffer_out1.set(signal)
            self.buffer_out2.set(silence)
        elif speaker == 'secondary':
            self.buffer_out1.set(silence)
            self.buffer_out2.set(signal)
        else:
            self.buffer_out1.set(signal)
            self.buffer_out2.set(signal)

    def select_speaker(self):
        if self.current_speaker_mode in ('primary', 'secondary', 'both'):
            return self.current_speaker_mode
        else:
            return 'primary' if np.random.uniform(0, 1) < 0.5 else 'secondary'

    def set_fa_puff_duration(self, value):
        self.iface_behavior.cset_tag('puff_dur_n', value, 's', 'n')

    def log_trial(self, ts_start, ts_end, last_ttype):
        self.model.data.log_trial(ts_start=ts_start, ts_end=ts_end,
                ttype=last_ttype, speaker=self.current_speaker,
                **self.current_context)

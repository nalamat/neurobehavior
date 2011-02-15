from enthought.traits.api import Any, Property, Str, on_trait_change

import numpy as np
from tdt import DSPCircuit
from cns.pipeline import deinterleave_bits
from cns.data.h5_utils import append_node, append_date_node, \
    get_or_append_node
from cns.data.persistence import add_or_update_object
from cns import choice
from functools import partial
from copy import deepcopy

from abstract_experiment_controller import AbstractExperimentController
from pump_controller_mixin import PumpControllerMixin
from aversive_data import RawAversiveData as AversiveData

import logging
log = logging.getLogger(__name__)

class AbstractAversiveController(AbstractExperimentController,
        PumpControllerMixin):
    # Derive from PumpControllerMixin since the code used to control the pump is
    # same regardless of whether it's positive or aversive paradigm.

    status = Property(Str, depends_on='state, current_+')

    '''
    Sequence of initialization
    * Configure variables
    * Hit the run (i.e. start) button
    * start_experiment is called
    '''

    def init_equipment(self):
        # I have broken this out into a separate function because
        # AversiveFMController needs to change the initialization sequence a
        # little (i.e. it needs to use different microcode and the microcode
        # does not contain int and trial buffers).
        self.iface_behavior = DSPCircuit('components/aversive-behavior', 'RZ6')
        self.buffer_trial = self.iface_behavior.get_buffer('trial', 'w')
        self.buffer_int = self.iface_behavior.get_buffer('int', 'w')
        self.buffer_TTL = self.iface_behavior.get_buffer('TTL', 'r',
                src_type='int8', dest_type='int8', block_size=24)
        self.buffer_contact = self.iface_behavior.get_buffer('contact', 'r',
                src_type='int8', dest_type='float32', block_size=24)

    def start_experiment(self, info):
        self.init_equipment()
        self.init_pump(info)
        self.init_paradigm(self.model.paradigm)

        # Ensure that sampling frequencies are stored properly
        self.model.data.contact_digital.fs = self.buffer_TTL.fs
        self.model.data.contact_digital_mean.fs = self.buffer_contact.fs
        self.model.data.trial_running.fs = self.buffer_TTL.fs
        self.model.data.shock_running.fs = self.buffer_TTL.fs
        self.model.data.warn_running.fs = self.buffer_TTL.fs

        # Since several streams of data are compressed into individual bits
        # (which are transmitted to the computer as an 8-bit integer), we need
        # to decompress them (via int_to_TTL) and store them in the appropriate
        # data buffers via deinterleave.
        targets = [ self.model.data.trial_running, 
                    self.model.data.contact_digital,
                    self.model.data.shock_running,
                    self.model.data.warn_running, ]
        self.pipeline_TTL = deinterleave_bits(targets)

        # The buffer for contact_digital_mean does not need any processing, so
        # we just grab it and pass it along to the data buffer.
        self.pipeline_contact = self.model.data.contact_digital_mean

        # Initialize signal buffers
        self.update_safe()
        self.update_warn()

        # We want to start the circuit in the paused state (i.e. playing the
        # intertrial signal but not presenting trials)
        self.pause()
        # Now we start the circuit
        self.iface_behavior.start()

        # We monitor current_trial_end_ts to determine when a trial is over.
        # Let's grab the current value of trial_end_ts before we do anything
        # else.  If we grab it before starting the circuit, then it may not
        # reflect any spurious triggers that cause trial_end_ts to advance
        # during initialization (this is very common when you have EdgeDetect
        # set to "falling edge" for detecting when a trial is over).  This is a
        # known bug and the easiest way to work around it is to let the circuit
        # initialize and "settle" before grabbing the relevant values.
        self.current_trial_ts = self.get_trial_end_ts()

    def remind(self, info=None):
        self.state = 'manual'
        self.update_remind()
        self.trigger_next()
        self.set_pause_state(False)

    def pause(self, info=None):
        self.log_event(self.get_ts(), 'pause', True)
        self.state = 'paused'
        self.set_pause_state(True)

    def resume(self, info=None):
        self.log_event(self.get_ts(), 'pause', False)
        self.state = 'running'
        self.set_pause_state(False)
        self.trigger_next()

    def stop_experiment(self, info=None):
        self.state = 'halted'
        self.iface_behavior.stop()

        self.model.analyzed.mask_mode = 'none'
        # Save the data in our newly created node
        #add_or_update_object(self.pump, self.model.exp_node, 'Pump')
        add_or_update_object(self.model.paradigm, self.model.exp_node, 'Paradigm')
        add_or_update_object(self.model.data, self.model.exp_node, 'Data')
        analyzed_node = get_or_append_node(self.model.data.store_node, 'Analyzed')
        add_or_update_object(self.model.analyzed, analyzed_node)

    def tick_slow(self):
        ts = self.get_ts()
        seconds = int(ts/self.iface_behavior.fs)
        self.monitor_pump()

    def tick_fast(self):
        self.update_safe()
        self.pipeline_TTL.send(self.buffer_TTL.read())
        self.pipeline_contact.send(self.buffer_contact.read())

        if self.current_trial_ts < self.get_trial_end_ts():
            ts_start = self.get_trial_start_ts()
            ts_end = self.get_trial_end_ts()
            self.current_trial_ts = ts_end

            ts = self.get_trial_contact_start_ts()

            # Process "reminder" signals
            if self.state == 'manual':
                self.pause()
                par = self.current_remind.parameter
                self.model.data.log_trial(ts, par, -1, 'remind')
                self.update_warn()
            else:
                last_trial = self.current_trial
                self.current_trial += 1

                # What do we need to do to get ready?
                if last_trial == self.current_num_safe + 1:
                    # The last trial was a warn trial.  Let's get a new
                    # current_par, compute a new num_safe, and update the warn
                    # signal.
                    log.debug('processing warning trial')
                    par = self.current_warn.parameter
                    self.model.data.log_trial(ts, par, -1, 'warn')
                    self.current_num_safe = self.choice_num_safe()
                    self.current_warn = self.choice_setting.next()

                    # If there are 3 safes, current trial will be 1, 2, 3, 4
                    # where 4 is the warn
                    self.current_trial = 1
                    log.debug('new num_safe %d, new par %f',
                              self.current_num_safe,
                              self.current_warn.parameter)
                    self.update_warn()
                elif last_trial <= self.current_num_safe: 
                    # The last trial was a safe trial
                    par = self.current_warn.parameter
                    self.model.data.log_trial(ts, par, 0, 'safe')
                else:
                    # Something bad happened
                    log.debug('last_trial: %d, current_num_safe %d', last_trial,
                              self.current_num_safe)
                    raise SystemError, 'There is a mismatch.'
                    
            # Signal to the circuit that data processing is done and it can
            # commence execution.
            self.trigger_next()

    def _get_status(self):
        if self.state == 'disconnected':
            return 'Cannot connect to equipment'
        if self.state == 'halted':
            return 'System is halted'
        if self.state == 'manual':
            return 'PAUSED: presenting reminder (%s)' % self.current_remind

        if self.current_trial > self.current_num_safe:
            status = 'WARNING (%s)' % self.current_warn
        else:
            mesg = 'SAFE %d of %d (%s)'
            status = mesg % (self.current_trial, self.current_num_safe,
                             self.current_warn)
        if self.state == 'paused':
            status = 'PAUSED: next trial is %s' % status
        return status

    ############################################################################
    # Code to apply parameter changes.  This is backend-specific.  If you want
    # to implement a new backend, you would subclass this and override the
    # appropriate set_* methods.
    ############################################################################

    def get_trial_contact_start_ts(self):
        return self.iface_behavior.get_tag('trial_contact/')

    def get_trial_start_ts(self):
        return self.iface_behavior.get_tag('trial/')

    def get_trial_end_ts(self):
        return self.iface_behavior.get_tag('trial\\')

    def get_ts(self):
        return self.iface_behavior.get_tag('zTime')

    def log_event(self, ts, name, value):
        self.model.data.log_event(ts, name, value)

    # Use a function called set_<parameter_name>.  This function will be called
    # when you change that parameter via the GUI and then click on the Apply
    # button.  These functions define how the change to the parameter should be
    # handled.  Variable names come from the attribute in the paradigm (i.e. if
    # a variable is called "par_seq_foo in the AversiveParadigm class, you would
    # define a function called "set_par_seq_foo".

    def set_order(self, value):
        self.current_order = value
        self.reset_sequence()

    def set_warn_sequence(self, value):
        self.current_warn_sequence = deepcopy(value)
        self.reset_sequence()

    def reset_sequence(self):
        order = self.current_order
        parameters = self.current_warn_sequence
        if order is not None and parameters is not None:
            self.choice_setting = choice.get(order, parameters)
            self.current_trial = 1
            if self.current_warn is None:
                self.current_warn = self.choice_setting.next()

    def set_min_safe(self, value):
        self.current_min_safe = value
        self.reset_safes()

    def set_max_safe(self, value):
        self.current_max_safe = value

    def reset_safes(self):
        lb = self.current_min_safe
        ub = self.current_max_safe
        if lb is not None and ub is not None:
            self.choice_num_safe = partial(np.random.randint, lb, ub+1)
            self.current_num_safe = self.choice_num_safe()

    def set_safe(self, value):
        self.current_safe = value

    def set_remind(self, value):
        self.current_remind = value

    def set_prevent_disarm(self, value):
        self.iface_behavior.set_tag('no_disarm', value)

    def set_aversive_delay(self, value):
        self.iface_behavior.cset_tag('aversive_del_n', value, 's', 'n')

    def set_aversive_duration(self, value):
        self.iface_behavior.cset_tag('aversive_dur_n', value, 's', 'n')

    def set_lick_th(self, value):
        self.iface_behavior.set_tag('lick_th', value)

    def set_pause_state(self, value):
        self.iface_behavior.set_tag('pause_state', value)

    def trigger_next(self):
        if self.state == 'manual':
            self.iface_behavior.set_tag('warn?', 1)
        elif self.current_trial == self.current_num_safe + 1:
            self.iface_behavior.set_tag('warn?', 1)
        else:
            self.iface_behavior.set_tag('warn?', 0)
        self.iface_behavior.trigger(1)

    def set_trial_duration(self, value):
        self.current_trial_duration = value
        self.iface_behavior.cset_tag('trial_dur_n', value, 's', 'n')
        # Now that we've changed trial duration, we need to be sure to update
        # the warn signal.  Since the safe signal is continuously being updated,
        # we don't need to update that.

        if self.current_warn is not None:
            self.update_warn()

    def set_attenuation(self, value):
        self.iface_behavior.set_tag('att_A', value)

    def update_remind(self):
        raise NotImplementedError

    def update_warn(self):
        raise NotImplementedError

    def update_safe(self):
        raise NotImplementedError

    @on_trait_change('model.paradigm.warn_sequence.+')
    def queue_warn_sequence_change(self, object, name, old, new):
        self.queue_change(self.model.paradigm, 'warn_sequence',
                self.current_warn_sequence, self.model.paradigm.warn_sequence)

    @on_trait_change('model.paradigm.remind.+')
    def queue_remind_change(self, object, name, old, new):
        self.queue_change(self.model.paradigm, 'remind',
                self.current_remind, self.model.paradigm.remind)

    @on_trait_change('model.paradigm.safe.+')
    def queue_safe_change(self, object, name, old, new):
        self.queue_change(self.model.paradigm, 'safe',
                self.current_safe, self.model.paradigm.safe)

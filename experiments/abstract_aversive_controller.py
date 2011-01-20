from enthought.traits.api import Any, Property, Str

from tdt import DSPCircuit
from cns.pipeline import deinterleave_bits
from cns.data.h5_utils import append_node, append_date_node, \
    get_or_append_node
from cns.data.persistence import add_or_update_object
from cns import choice

from abstract_experiment_controller import AbstractExperimentController
from pump_controller_mixin import PumpControllerMixin
from aversive_data import RawAversiveData as AversiveData

import logging
log = logging.getLogger(__name__)

class AbstractAversiveController(AbstractExperimentController,
        PumpControllerMixin):
    # Derive from PumpControllerMixin since the code used to control the pump is
    # same regardless of whether it's positive or aversive paradigm.

    exp_node = Any
    data_node = Any

    status = Property(Str, depends_on='state, current_+')

    '''
    Sequence of initialization
    * Configure variables
    * Hit the run (i.e. start) button
    * start_experiment is called
    * start_experiment calls init_equipment and init_current
    '''

    def init_current(self, info=None):
        # instance of aversive_paradigm.AversiveParadigm
        paradigm = self.model.paradigm 

        # Copy all paradigm parameters over to the controller as attributes
        # called current_<parameter name>
        self.copy_paradigm(paradigm)

        self.choice_setting = choice.get(self.current_order,
                                         self.current_warn_sequence)
        trials = range(self.current_min_safe, self.current_max_safe+1)
        self.choice_num_safe = choice.get('pseudorandom', trials)

        # choice_par and choice_num_safe are generators (i.e. functions that
        # remember their state in between calls).  Thus, they are a great way
        # for tracking what the next parameter and number of safes should be.
        #self.choice_par = choice.get(paradigm.par_order, paradigm.pars[:])

        self.current_warn = self.choice_setting.next()
        self.current_num_safe = self.choice_num_safe.next()
        self.current_trial = 1

    def init_equipment(self):
        # I have broken this out into a separate function because
        # AversiveFMController needs to change the initialization sequence a
        # little (i.e. it needs to use different microcode and the microcode
        # does not contain int and trial buffers).
        self.iface_behavior = DSPCircuit('components/aversive-behavior', 'RZ6')
        self.buffer_trial = self.iface_behavior.get_buffer('trial')
        self.buffer_int = self.iface_behavior.get_buffer('int')
        self.buffer_TTL = self.iface_behavior.get_buffer('TTL',
                src_type='int8', dest_type='int8', block_size=24)
        self.buffer_contact = self.iface_behavior.get_buffer('contact',
                src_type='int8', dest_type='float32', block_size=24)

    def start_experiment(self, info):
        self.init_equipment()
        self.init_pump(info)

        # Set up the data node
        self.model.exp_node = append_date_node(self.model.store_node,
                pre='aversive_date_')
        log.debug('Created experiment node for experiment at %r',
                self.model.exp_node)
        self.model.data_node = append_node(self.model.exp_node, 'Data')
        log.debug('Created data node for experiment at %r', self.model.data_node)
        self.model.data = AversiveData(store_node=self.model.data_node)

        self.init_current(info)

        # Be sure that all relevant circuit parameters are set properly before
        # we start the experiment! 
        self.set_aversive_delay(self.model.paradigm.aversive_delay)
        self.set_aversive_duration(self.model.paradigm.aversive_duration)
        self.set_contact_threshold(self.model.paradigm.lick_th)
        self.set_trial_duration(self.model.paradigm.trial_duration)
        self.set_attenuation(self.model.paradigm.attenuation)

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

        # We monitor current_trial_end_ts to determine when a trial is over.
        # Let's grab the current value of trial_end_ts
        self.current_trial_ts = self.get_trial_end_ts()
        # We want to start the circuit in the paused state (i.e. playing the
        # intertrial signal but not presenting trials)
        self.pause()
        # Now we start the circuit
        self.iface_behavior.start()
        # The circuit requires a "high" zBUS trigger A to enable data collection
        self.iface_behavior.trigger('A', 'high')

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
                    self.current_num_safe = self.choice_num_safe.next()
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
            return 'PAUSED: presenting reminder (%r)' % self.current_par

        if self.current_trial > self.current_num_safe:
            status = 'WARNING (%r)' % self.current_par
        else:
            mesg = 'SAFE %d of %d (%r)'
            status = mesg % (self.current_trial, self.current_num_safe, self.current_par)
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

    # Tells controller to reset current trial settings once all changes are
    # applied.  This should only be used when you need to change the trial
    # sequence (i.e. number of safes, order of parameters, parameter sequence,
    # etc).
    set_remind           = AbstractExperimentController.reset_current
    set_safe             = AbstractExperimentController.reset_current
    set_order            = AbstractExperimentController.reset_current
    set_max_safe         = AbstractExperimentController.reset_current
    set_min_safe         = AbstractExperimentController.reset_current

    # Use a function called set_<parameter_name>.  This function will be called
    # when you change that parameter via the GUI and then click on the Apply
    # button.  These functions define how the change to the parameter should be
    # handled.  Variable names come from the attribute in the paradigm (i.e. if a variable
    # is called "par_seq_foo in the AversiveParadigm class, you would define a
    # funciton called "set_par_seq_foo".

    def set_aversive_delay(self, value):
        self.iface_behavior.cset_tag('aversive_del_n', value, 's', 'n')

    def set_aversive_duration(self, value):
        self.iface_behavior.cset_tag('aversive_dur_n', value, 's', 'n')

    def set_contact_threshold(self, value):
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
        print self.iface_behavior.get_tag('foobar')
        self.iface_behavior.trigger(1)

    def set_trial_duration(self, value):
        self.current_trial_duration = value
        self.iface_behavior.cset_tag('trial_dur_n', value, 's', 'n')
        # Now that we've changed trial duration, we need to be sure to update
        # the warn signal.  Since the safe signal is continuously being updated,
        # we don't need to update that.
        self.update_warn()

    def set_attenuation(self, value):
        self.iface_behavior.set_tag('att_A', value)

    def update_remind(self):
        raise NotImplementedError

    def update_warn(self):
        raise NotImplementedError

    def update_safe(self):
        raise NotImplementedError

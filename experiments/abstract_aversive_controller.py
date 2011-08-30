from enthought.traits.api import Property
from cns.pipeline import deinterleave_bits
from abstract_experiment_controller import AbstractExperimentController
from cns import get_config
from os.path import join

import logging
log = logging.getLogger(__name__)

class AbstractAversiveController(AbstractExperimentController):

    def _setup_circuit(self):
        # I have broken this out into a separate function because
        # AversiveFMController needs to change the initialization sequence a
        # little (i.e. it needs to use different microcode and the microcode
        # does not contain int and trial buffers).
        circuit = join(get_config('RCX_ROOT'), 'aversive-behavior')
        self.iface_behavior = self.process.load_circuit(circuit, 'RZ6')

        # Initialize the buffers
        self.buffer_trial = self.iface_behavior.get_buffer('trial', 'w')
        self.buffer_int = self.iface_behavior.get_buffer('int', 'w')
        self.buffer_TTL = self.iface_behavior.get_buffer('TTL', 'r',
                src_type='int8', dest_type='int8', block_size=24)
        self.buffer_contact = self.iface_behavior.get_buffer('contact', 'r',
                src_type='int8', dest_type='float32', block_size=24)

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

    def setup_experiment(self, info):
        self._setup_circuit()

        # Pump will halt when it has infused the requested volume.  To allow it
        # to infuse continuously, we set the volume to 0.
        self.iface_pump.set_volume(0)
        # Pump will start on a rising edge (e.g. the subject touches the spout)
        # and stop on a falling edge (e.g. the subject leaves the spout).
        self.iface_pump.set_trigger(start='rising', stop='falling')

    def start_experiment(self, info):
        self.initialize_context()

        # We monitor current_trial_end_ts to determine when a trial is over.
        # Let's grab the current value of trial_end_ts before we do anything
        # else.  If we grab it before starting the circuit, then it may not
        # reflect any spurious triggers that cause trial_end_ts to advance
        # during initialization (this is very common when you have EdgeDetect
        # set to "falling edge" for detecting when a trial is over).  This is a
        # known bug and the easiest way to work around it is to let the circuit
        # initialize and "settle" before grabbing the relevant values.
        self.current_trial_ts = self.get_trial_end_ts()

        # We want to start the circuit in the paused state (i.e. playing the
        # intertrial signal but not presenting trials)
        self.pause()
        
        self.tasks.append((self.monitor_pump, 5))
        self.tasks.append((self.monitor_behavior, 1))

    def remind(self, info=None):
        # Pause circuit and see if trial is running. If trial is already
        # running, it's too late and a lock cannot be acquired. If trial is not
        # running, changes can be made. A lock is returned (note this is not
        # thread-safe).
        self.remind_requested = True
        self.trigger_next()

    def request_pause(self):
        self.iface_behavior.trigger(2)
        return self.get_pause_state()

    def request_resume(self):
        self.iface_behavior.trigger(3)

    def pause(self, info=None):
        self.log_event('pause', True)
        self.state = 'paused'
        self.iface_behavior.trigger(2)

    def resume(self, info=None):
        self.log_event('pause', False)
        self.state = 'running'
        self.iface_behavior.trigger(3)
        self.trigger_next()

    def stop_experiment(self, info=None):
        self.model.analyzed.mask_mode = 'none'

    def log_trial(self, ts_start, ts_end, ttype):
        self.model.data.log_trial(ts_start=ts_start, ts_end=ts_end,
                                  ttype=last_ttype,
                                  speaker=self.current_speaker,
                                  **self.current_context)

    def monitor_behavior(self):
        self.update_safe()
        self.pipeline_TTL.send(self.buffer_TTL.read())
        self.pipeline_contact.send(self.buffer_contact.read())
        ts_end = self.get_trial_end_ts()

        if ts_end > self.current_trial_ts:
            self.current_trial_ts = ts_end
            ts_start = self.get_trial_start_ts()
            self.log_trial(ts_start, ts_end, self.current_ttype)
            self.trigger_next()

    ############################################################################
    # Code to apply parameter changes.  This is backend-specific.  If you want
    # to implement a new backend, you would subclass this and override the
    # appropriate set_* methods.
    ############################################################################

    def get_trial_start_ts(self):
        return self.iface_behavior.get_tag('trial/')

    def get_trial_end_ts(self):
        return self.iface_behavior.get_tag('trial\\')

    def get_ts(self):
        return self.iface_behavior.get_tag('zTime')

    # Use a function called set_<parameter_name>.  This function will be called
    # when you change that parameter via the GUI and then click on the Apply
    # button.  These functions define how the change to the parameter should be
    # handled.  Variable names come from the attribute in the paradigm (i.e. if
    # a variable is called "par_seq_foo in the AversiveParadigm class, you would
    # define a function called "set_par_seq_foo".

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

    def set_attenuation(self, value):
        self.iface_behavior.set_tag('att_A', value)

    def trigger_next(self):
        self.invalidate_context()
        self.current_ttype, self.current_setting = self.next_setting()
        self.evaluate_pending_expressions(self.current_setting)
        self.iface_behavior.trigger(1)

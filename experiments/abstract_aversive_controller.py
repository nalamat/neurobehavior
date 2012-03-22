from enthought.traits.api import Int, Any, Float
from cns.pipeline import deinterleave_bits
from abstract_experiment_controller import AbstractExperimentController
from cns import get_config
from os.path import join
import numpy as np

import logging
log = logging.getLogger(__name__)

class AbstractAversiveController(AbstractExperimentController):

    # Used to convert timestamp data (which should be stored at the maximum
    # sampling frequency of the DSP) to the TTL and contact sampling frequency
    # (critcal for computing lick_offset, etc).
    fs_conversion = Int
    pipeline_TTL = Any

    kw = {'context': True, 'log': True, 'immediate': True}
    hw_att1 = Float(120, **kw)
    hw_att2 = Float(120, **kw)

    def _setup_shock(self):
        # First, we need to load the circuit we need to control the shocker.
        # We currently use DAC channel 12 of the RZ5 to control shock level;
        # however, the RZ5 will already have a circuit loaded if we're using it
        # for physiology.  The physiology circuit is already configured to
        # control the shocker.  However, if we are not acquiring physiology, we
        # need to load a circuit that allows us to control the shocker.
        if not self.model.spool_physiology:
            circuit = join(get_config('RCX_ROOT'), 'shock-controller')
            self.iface_shock = self.process.load_circuit(circuit, 'RZ5')
        else:
            # This assumes that iface_physiology has already been initialized.
            # In the current abstract_experiment_controller, setup_physiology is
            # called before setup_experiment.  self.physiology_handler is a
            # reference to the PhysiologyController object.
            self.iface_shock = self.physiology_handler.iface_physiology

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
        self.buffer_spout_start = self.iface_behavior.get_buffer('spout/', 'r',
                src_type='int32', block_size=1)
        self.buffer_spout_end = self.iface_behavior.get_buffer('spout\\', 'r',
                src_type='int32', block_size=1)

    def _setup_pump(self):
        # Pump will halt when it has infused the requested volume.  To allow it
        # to infuse continuously, we set the volume to 0.
        self.iface_pump.set_volume(0)
        # Pump will start on a rising edge (e.g. the subject touches the spout)
        # and stop on a falling edge (e.g. the subject leaves the spout).
        self.iface_pump.set_trigger(start='rising', stop='falling')

    def setup_experiment(self, info):
        self._setup_pump()
        self._setup_shock()
        self._setup_circuit()

        # Ensure that sampling frequencies are stored properly
        self.model.data.contact_digital.fs = self.buffer_TTL.fs
        self.model.data.contact_digital_mean.fs = self.buffer_contact.fs
        self.model.data.trial_running.fs = self.buffer_TTL.fs
        self.model.data.shock_running.fs = self.buffer_TTL.fs
        self.model.data.warn_running.fs = self.buffer_TTL.fs

        self.model.data.trial_epoch.fs = self.iface_behavior.fs
        self.model.data.spout_epoch.fs = self.iface_behavior.fs
        self.model.data.reaction_ts.fs = self.iface_behavior.fs

        # Since several streams of data are compressed into individual bits
        # (which are transmitted to the computer as an 8-bit integer), we need
        # to decompress them (via int_to_TTL) and store them in the appropriate
        # data buffers via deinterleave.
        targets = [ self.model.data.trial_running, 
                    self.model.data.contact_digital,
                    self.model.data.shock_running,
                    self.model.data.warn_running, ]
        self.pipeline_TTL = deinterleave_bits(targets)
        self.fs_conversion = self.iface_behavior.get_tag('TTL_d')

        # The buffer for contact_digital_mean does not need any processing, so
        # we just grab it and pass it along to the data buffer.
        self.pipeline_contact = self.model.data.contact_digital_mean

    def start_experiment(self, info):
        # We monitor current_trial_end_ts to determine when a trial is over.
        # Let's grab the current value of trial_end_ts before we do anything
        # else.  If we grab it before starting the circuit, then it may not
        # reflect any spurious triggers that cause trial_end_ts to advance
        # during initialization (this is very common when you have EdgeDetect
        # set to "falling edge" for detecting when a trial is over).  This is a
        # known bug and the easiest way to work around it is to let the circuit
        # initialize and "settle" before grabbing the relevant values.
        self.current_trial_ts = self.get_trial_end_ts()

        # Sometimes the gerbil will not react until *after* the trial is over,
        # in which case no new timestamp is stored (the value of the timestamp
        # will reflect the prior trial).  Hence, we store a copy of the last
        # reaction timestamp so we can check it with the timestamp of the
        # current trial.  If it hasn't changed, then we know that the subject
        # did not react.
        self.current_react_ts = self.get_reaction_ts()

        # We want to start the circuit in the paused state (i.e. playing the
        # intertrial signal but not presenting trials)
        self.pause()
        self.tasks.append((self.monitor_pump, 5))
        self.tasks.append((self.monitor_behavior, 1))

        # We need to make sure that the pump rate and safe signal are playing
        # before the animal is put in the cage, we prepare the next trial *now*
        # (but don't trigger it).  Furthermore, we need to load the intertrial
        # buffer with the entire waveform before we start the experiment).
        self.fs_conversion = self.iface_behavior.get_tag('TTL_d')
        self.prepare_next()
        self.process.trigger('A', 'high')

    def remind(self, info=None):
        # Pause circuit and see if trial is running. If trial is already
        # running, it's too late and a lock cannot be acquired. If trial is not
        # running, changes can be made. A lock is returned (note this is not
        # thread-safe).
        self.remind_requested = True
        self.trigger_next()

    def pause(self, info=None):
        self.iface_behavior.trigger(2)
        self.log_event('pause', True)
        self.state = 'paused'

    def resume(self, info=None):
        self.log_event('pause', False)
        self.state = 'running'
        self.trigger_next()

    def stop_experiment(self, info=None):
        self.model.data.mask_mode = 'none'
        self.process.trigger('A', 'low')

    def monitor_behavior(self):
        # Always refresh the intertrial buffer with new data
        self.update_intertrial()

        # Grab new data
        self.pipeline_TTL.send(self.buffer_TTL.read())
        self.pipeline_contact.send(self.buffer_contact.read())
        self.model.data.spout_epoch.send(self.get_spout_epochs())

        # Check to see if a trial just completed
        ts_end = self.get_trial_end_ts()

        if ts_end > self.current_trial_ts:
            self.current_trial_ts = ts_end

            # Note that the ts_start and ts_end were originally recorded at the
            # sampling frequency of the TTL data.  However, we now have switched
            # to sampling ts_start and ts_end at a much higher resolution so we
            # can better understand the timing of the system.  The high
            # resolution ts_start and ts_end are stored in the trial_epoch array
            # in the data file while the low resolution (sampled at the TTL
            # rate) are stored in the trial log.
            ts_end = np.floor(ts_end/self.fs_conversion)
            ts_start = np.floor(self.get_trial_start_ts()/self.fs_conversion)
            self.log_trial(ts_start=ts_start, ts_end=ts_end)

            self.model.data.trial_epoch.send([self.get_trial_epoch()])
            react_ts = self.get_reaction_ts()
            if react_ts == self.current_react_ts:
                # Subject did not react before end of trial
                self.model.data.reaction_ts.send([np.nan])
            else:
                self.model.data.reaction_ts.send([react_ts])
                self.current_react_ts = react_ts

            # Only trigger the next trial if the system is running (if someone
            # presents a manual reminder, then the system will be in the
            # "paused" state)
            if self.state == 'running':
                self.trigger_next()

    ############################################################################
    # Code to apply parameter changes.  This is backend-specific.  If you want
    # to implement a new backend (e.g. use National Instruments instead of TDT),
    # you would subclass this and override the appropriate set_* and get_*
    # methods.
    ############################################################################

    def set_attenuations(self, att1, att2):
        # Attenuations can be None, in which case it means don't change
        # attenuation
        if att1 is None:
            att1 = self.hw_att1
        if att2 is None:
            att2 = self.hw_att2

        if att1 != self.hw_att1:
            self.hw_att1 = att1
            self.iface_behavior.set_tag('att1', att1)
            log.debug('Updated primary attenuation to %.2f', att1)
        if att2 != self.hw_att2:
            self.hw_att2 = att2
            self.iface_behavior.set_tag('att2', att2)
            log.debug('Updated secondary attenuation to %.2f', att2)

    def get_reaction_ts(self):
        return self.iface_behavior.get_tag('react|')

    def get_trial_start_ts(self):
        return self.iface_behavior.get_tag('trial/')

    def get_trial_end_ts(self):
        return self.iface_behavior.get_tag('trial\\')

    def get_trial_epoch(self):
        return (self.get_trial_start_ts(), self.get_trial_end_ts())

    def get_spout_epochs(self):
        ends = self.buffer_spout_end.read().ravel()
        starts = self.buffer_spout_start.read(len(ends)).ravel()
        return zip(starts, ends)

    def get_ts(self):
        return self.iface_behavior.get_tag('zTime')

    def set_prevent_disarm(self, value):
        self.iface_behavior.set_tag('no_disarm', value)

    def set_aversive_delay(self, value):
        self.iface_behavior.cset_tag('aversive_del_n', value, 's', 'n')

    def set_aversive_duration(self, value):
        self.iface_behavior.cset_tag('aversive_dur_n', value, 's', 'n')

    def set_lick_th(self, value):
        self.iface_behavior.set_tag('lick_th', value)

    def set_trial_duration(self, value):
        self.iface_behavior.cset_tag('trial_dur_n', value, 's', 'n')

    def is_warn(self):
        return self.current_setting.ttype.startswith('GO')

    def prepare_next(self):
        self.invalidate_context()
        self.current_setting = self.next_setting()
        self.evaluate_pending_expressions(self.current_setting)
        self.update_intertrial()
        self.update_trial()

    def trigger_next(self):
        self.prepare_next()
        self.iface_behavior.set_tag('warn?', self.is_warn())
        self.iface_behavior.trigger(1)

    def set_shock_level(self, value):
        '''
         Programmable input ranges from 0 to 2.5 V corresponding to a 0 to 5 mA
         range.  Divide by 2.0 to convert mA to the corresponding shock level.
         When set to manual high, use the lower scale to read the meter.
        
         * iface_shock is a reference to the tdt.DSPCircuit that communicates
         with the RZ5 (i.e. the shock-controller.rcx circuit when running
         behavior only or the physiology.rcx circuit when running both phys and
         behavior)
         * iface_behavior is a reference to the tdt.DSPCircuit that
         communicates with the RZ6 (i.e. the aversive-behavior.rcx or one of the
         modified versions such as the aversive-behavior-fmam.rcx)
         
         We need to disable the shock trigger when shock_level is set to 0
         because the shocker still generates a small current at this level.

         iface is short for "interface"
         '''
        self.iface_behavior.set_tag('do_shock', bool(value))
        self.iface_shock.set_tag('shock_level', value/2.0)

    def cancel_trigger(self):
        self.iface_behavior.trigger(2)
        return not self.trial_running()

    def cancel_remind(self, info):
        self.iface_behavior.trigger(2)

    def trial_running(self):
        return self.iface_behavior.get_tag('trial_running')

    def _context_updated_fired(self):
        if self.cancel_trigger():
            self.prepare_next()
            if self.state == 'running':
                self.trigger_next()

    def update_intertrial(self):
        '''
        Must be defined in a subclass
        
        See docstring for update_trial
        '''
        raise NotImplementedError

    def update_trial(self):
        '''
        Must be defined in a subclass.

        Ultimately, the waveform must be uploaded to the TDT stimulus
        generation DSP (i.e. the RZ6) by this function.  The waveform can be
        generated using neurogen or via a "script" approach.

        The relevant variables needed are:

            self.iface_behavior
            Reference to the DSPCircuit wrapper for the TDT stimulus generation DSP 
        self.iface_behavior.fs
            Sampling frequency of the stimulus generation DSP (same value as
            that returned by GetSFreq()
        self.buffer_int
            Reference to the hardware buffer on the stimulus generation DSP
            responsible for holding the intertrial waveform (can be set to a
            string of zeros for silence).
        self.buffer_trial
            Reference to the hardware buffer on the stimulus generation DSP
            responsible for holding the trial waveform (note that this applies
            to both the safe/nogo and warn/go trials).
        self.cal_primary
            Reference to the calibration for the primary speaker.  See the
            documentation in neurogen.calibration.Calibration for more
            information.
        self.cal_secondary
            Reference to the calibration for the secondary speaker.

        To get the current value of the parameters defined in your paradigm class:

        center_frequency = self.get_current_value('center_frequency')
        modulation_depth = self.get_current_value('modulation_depth')

        Very important!  If you modify the current value of one of these
        parameters in this method, you must be sure to update the value so it
        is correctly saved in the trial log.  To do so:

        self.set_current_value('center_frequency', 4e3)

        To update the hardware attenuators, use the set_attenuations method.  

        self.set_attenuations(att1, att2, mode='full')

        By default, the buffer will switch immediately from the intertrial
        buffer to the beginning of the trial buffer when all conditions for
        starting a trial have been met.  However, you can ensure that this
        switch occurs only at certain points in the intertrial buffer by
        setting the `intertrial_n` tag in the DSPCircuit.  If your intertrial
        buffer repeats every 100 samples, then you can ensure that the
        transition only occurs at the end of a given period:
        
        self.iface_behavior.set_tag('intertrial_n', 100)

        But this has not been rigorously tested.
        '''
        raise NotImplementedError

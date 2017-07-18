'''
Appetitive comodulation masking release (continuous noise)
----------------------------------------------------------
:Authors: **Brad Buran <bburan@alum.mit.edu>**
          **Antje Ihlefeld <ai33@nyu.edu>**
          **Nima Alamatsaz <nima.alamatsaz@njit.edu>**

:Method: Constant limits go-nogo
:Status: Alpha.  Currently under development and testing.

    param1 : unit
        description
    param2 : unit
        description

Although this is a constant limits go-nogo paradigm, there are several key
differences between this paradigm and `positive_dt_cl` and
`positive_am_noise_cl`::

    * The target is added to a continuous masker (masker is specified by
    `masker_filename` which must contain float32 values stored as binary).

    * Both the target and masker waveforms are pregenerated using a script
    and saved to a file in float32 binary format.  The correct file to read for
    the target is determined by data stored in the `go_filename` and
    `nogo_filename` CSV files.

Due to the nature of how the target and masker are generated and combined, the
experimenter must determine the appropriate hardware attenuation.  There is a
field under the paradigm tab in the GUI that allows the hardware attenuation to
be set to the appropriate step (e.g. 0, 20, 40 or 60 dB).
'''

from __future__ import division

# Available as a built-in module starting with Python 3.4. Backported to python
# 2.7 using the enum34 module. May need to install the enum34 module if not
# already installed. Can remove once we migrate completely to Python 3.4+.
import enum

import threading
import sys
from os import path
import win32api
from time import time
from Queue import Queue

from traits.api import Instance, File, Any, Int, Bool
from traitsui.api import View, Include, VGroup, HGroup

from experiments.evaluate import Expression

from cns import get_config

# These mixins are shared with the positive_cmr_training p  aradigm.  I use the
# underscore so it's clear that these files do not define stand-alone paradigms.
from ._positive_cmr_mixin import PositiveCMRParadigmMixin
from ._positive_cmr_mixin import PositiveCMRControllerMixin

from daqengine.ni import Engine

import numpy as np
from scipy.io import wavfile

# __name__ is a special variable available to the module that will be
# "paradigms.positive_cmr" (i.e. the "name" of the module as seen by Python).
import logging
log = logging.getLogger(__name__)

from experiments.abstract_experiment_controller  import AbstractExperimentController
from experiments.positive_stage1_controller_v2   import PositiveStage1Controller
from experiments.abstract_positive_experiment_v3 import AbstractPositiveExperiment
from experiments.abstract_positive_paradigm_v3   import AbstractPositiveParadigm
from experiments.positive_stage1_paradigm_v2     import PositiveStage1Paradigm
from experiments.positive_data_v3                import PositiveData

from experiments.pump_controller_mixin           import PumpControllerMixin
from experiments.pump_paradigm_mixin             import PumpParadigmMixin
from experiments.pump_data_mixin                 import PumpDataMixin

from experiments.cl_controller_mixin             import CLControllerMixin
from experiments.cl_paradigm_mixin               import CLParadigmMixin
from experiments.cl_experiment_mixin             import CLExperimentMixin
from experiments.positive_cl_data_mixin          import PositiveCLDataMixin


class TrialState(enum.Enum):
    '''
    Defines the possible states that the experiment can be in. We use an Enum to
    minimize problems that arise from typos by the programmer (e.g., they may
    accidentally set the state to "waiting_for_nose_poke_start" rather than
    "waiting_for_poke_start").

    This is specific to appetitive reinforcement paradigms.
    '''
    waiting_for_poke_start    = 'waiting for nose-poke start'
    waiting_for_poke_duration = 'waiting for nose-poke duration'
    waiting_for_hold_period   = 'waiting for hold period'
    waiting_for_response      = 'waiting for response'
    waiting_for_to            = 'waiting for timeout'
    waiting_for_iti           = 'waiting for intertrial interval'


class Event(enum.Enum):
    '''
    Defines the possible events that may occur during the course of the
    experiment.

    This is specific to appetitive reinforcement paradigms.
    '''
    poke_start                = 'initiated nose poke'
    poke_end                  = 'withdrew from nose poke'
    poke_duration_elapsed     = 'nose poke duration met'
    hold_duration_elapsed     = 'hold period over'
    response_duration_elapsed = 'response timed out'
    spout_start               = 'spout contact'
    spout_end                 = 'withdrew from spout'
    to_duration_elapsed       = 'timeout over'
    iti_duration_elapsed      = 'ITI over'
    trial_start               = 'trial start'
    button_push               = 'button push'
    button_release            = 'button release'


class Controller(
        PositiveCMRControllerMixin,
        # AbstractExperimentController,
        PositiveStage1Controller,
        CLControllerMixin,
        PumpControllerMixin,
        ):
    '''
    Controls experiment logic (i.e. communicates with the NI hardware,
    responds to input by the user, etc.).
    '''
    random_generator = Any
    random_seed = Int
    remind_requested = Bool

    # Track the current state of the experiment. How the controller responds to
    # events will depend on the state.
    trial_state = Instance(TrialState, TrialState.waiting_for_poke_start)

    def _get_status(self):
        return self.trial_state.value

    preload_samples = 200000*5
    update_delay = 200 # ms

    _lock = threading.Lock()
    engine = Instance('daqengine.ni.Engine')

    fs = 100e3
    masker_on = False
    target_on = False
    target_ts = 0
    light_on = False

    def apply(self, info=None):
        AbstractExperimentController.apply(self, info)
        if self.state is 'paused':
            self.refresh_context()
            self.set_pump_rate(self.get_current_value('pump_rate'))
            self.set_pump_volume(self.get_current_value('reward_volume'))

    def setup_experiment(self, info):
        return

    def start_experiment(self, info):
        self.refresh_context()

        # Load the masker and target. Scale to +/-1 V based on the maximum value
        # of a signed 16 bit integer. Right now we assume that the nogo is
        # silent (i.e., a scaling factor of 0). Go trials will have a nonzero
        # scaling factor. In general, this is a fairly reasonable approximation
        # of SDT (i.e., the nogo should be some undetectable variant of the go,
        # right)?
        # test_sf = 10.0**(self.get_current_value('test_att')/-20.0)

        masker_filename = self.get_current_value('masker_filename')
        if not path.exists(masker_filename):
            m = 'Masker file {} does not exist'
            raise ValueError(m.format(masker_filename))
        self.masker_offset = 0
        self.masker_last_write = 0
        self.fs, masker = wavfile.read(masker_filename, mmap=True)
        self.masker = masker.astype('float64')/np.iinfo(np.int16).max

        target_filename = self.get_current_value('target_filename')
        if not path.exists(target_filename):
            m = 'Go file {} does not exist'
            raise ValueError(m.format(target_filename))
        self.target_offset = 0
        self.fs, target_flat = wavfile.read(target_filename[:-4]+'_flat'+target_filename[-4:], mmap=True)
        self.fs, target_ramp = wavfile.read(target_filename[:-4]+'_ramp'+target_filename[-4:], mmap=True)
        self.target_flat = target_flat.astype('float64')/np.iinfo(np.int16).max
        self.target_ramp = target_ramp.astype('float64')/np.iinfo(np.int16).max

        self.trial_state = TrialState.waiting_for_poke_start
        self.engine = Engine()

        # Speaker in, mic, nose-poke IR, spout contact IR. Not everything will
        # necessarily be connected.
        self.fs_ai = 250e3/4
        self.engine.configure_hw_ai(self.fs_ai, '/Dev2/ai0:3', (-10, 10),
                                    names=['speaker', 'mic', 'poke', 'spout'])

        # Speaker out
        self.engine.configure_hw_ao(self.fs, '/Dev2/ao0', (-10, 10),
                                    names=['speaker'])

        # Nose poke and spout contact TTL. If we want to monitor additional
        # events occuring in the behavior booth (e.g., room light on/off), we
        # can connect the output controlling the light/pump to an input and
        # monitor state changes on that input.
        self.engine.configure_hw_di(self.fs, '/Dev2/port0/line1:3',
                                    clock='/Dev2/Ctr0',
                                    names=['spout', 'poke', 'button'])

        # Control for room light
        self.engine.configure_sw_do('/Dev2/port1/line1', names=['light'])
        self.engine.set_sw_do('light', 1)
        self.light_on = True

        self.engine.register_ao_callback(self.samples_needed)
        self.engine.register_ai_callback(self.samples_acquired)
        self.engine.register_di_change_callback(self.di_changed,
                                                debounce=self.fs*50e-3)

        self.model.data.speaker.fs    = self.fs_ai
        self.model.data.microphone.fs = self.fs_ai
        self.model.data.poke.fs         = self.fs_ai
        self.model.data.spout.fs      = self.fs_ai

        # Configure the pump
        if not self.model.args.nopump:
            self.iface_pump.set_direction('infuse')

        # Generate a random seed based on the computer's clock.
        self.random_seed = int(time())

        self.random_generator = np.random.RandomState(self.random_seed)

        node = info.object.experiment_node
        node._v_attrs['trial_sequence_random_seed'] = self.random_seed

        self.set_current_value('ttype', 'GO')

        self.state = 'paused'
        self.engine.start()
        # self.trigger_next()

    # def trigger_next(self):
    #     self.trial_info = {}
    #     self.invalidate_context()
    #     self.current_setting = self.next_setting()
    #     self.evaluate_pending_expressions(self.current_setting)

    def log_trial(self, **kwargs):
        # HDF5 data files do not natively support unicode strings so we need to
        # convert our filename to an ASCII string.  While we're at it, we should
        # probably strip the directory path as well and just save the basename.
        target_filename = self.get_current_value('target_filename')
        kwargs['target_filename'] = str(path.basename(target_filename))
        masker_filename = self.get_current_value('masker_filename')
        kwargs['masker_filename'] = str(path.basename(masker_filename))
        super(Controller, self).log_trial(**kwargs)

    def stop_experiment(self, info):
        self.engine.stop()
        if not self.model.args.nopump:
            self.iface_pump.disconnect()

    def request_remind(self, info=None):
        # If trial is already running, the remind will be presented on the next
        # trial.
        self.remind_requested = True

    def start_trial(self):
        self.target_play()
        self.set_current_value('ttype', 'GO')

        # TODO - the hold duration will include the update delay. Do we need
        # super-precise tracking of hold period or can it vary by a couple 10s
        # to 100s of msec?
        self.trial_state = TrialState.waiting_for_hold_period
        self.start_timer('hold_duration', Event.hold_duration_elapsed)

    def stop_trial(self, response):
        trial_type = self.get_current_value('ttype')
        # if response != 'no response':
        #     self.trial_info['response_time'] = \
        #         self.trial_info['response_ts']-self.trial_info['target_start']
        # else:
        #     self.trial_info['response_time'] = np.nan

        # self.trial_info['reaction_time'] = \
        #     self.trial_info.get('poke_end', np.nan)-self.trial_info['poke_start']

        if trial_type in ('GO', 'GO_REMIND'):
            score = 'HIT' if response == 'spout contact' else 'MISS'
        elif trial_type in ('NOGO', 'NOGO_REPEAT'):
            score = 'FA' if response == 'spout contact' else 'CR'

        if score == 'FA':
            # Turn the light off
            self.engine.set_sw_do('light', 0)
            self.light_on = False
            self.start_timer('to_duration', Event.to_duration_elapsed)
            self.trial_state = TrialState.waiting_for_to
        else:
            if score == 'HIT':
                # TODO: Investigate why are changes to reward_volume applied on
                # the second trial rather than the first one?
                if not self.model.args.nopump:
                    self.pump_trigger([])

            self.start_timer('iti_duration', Event.iti_duration_elapsed)
            self.trial_state = TrialState.waiting_for_iti

        # Overrwrite output buffer with the masker to stop sound
        # ts = self.get_ts()
        # ud = self.get_current_value('update_delay')*1e-3 # Convert msec to sec
        # offset = int(round((ts+ud)*self.fs))
        # duration = self.get_target().shape[-1]
        # signal = self.get_masker(offset, duration)
        # try:
        #     self.engine.write_hw_ao(signal, offset)
        #     self.masker_offset = offset + duration
        # except:
        #     log.error(sys.exc_info()[1])

        # print(self.trial_info)
        # self.log_trial(score=score, response=response, ttype=trial_type,
        #                **self.trial_info)
        # self.trigger_next()


    def context_updated(self):
        self.refresh_context()
        # self.current_setting = self.next_setting()
        # self.evaluate_pending_expressions(self.current_setting)
        # if self.trial_state == TrialState.waiting_for_poke_start:
        #     self.trigger_next()


    def target_play(self, info=None):
        # Get the current position in the analog output buffer, and add a cetain
        # update_delay (to give us time to generate and upload the new signal).

        try:
            ts = self.get_ts()
            ud = self.update_delay*1e-3 # Convert msec to sec
            offset = int(round((ts+ud)*self.fs))

            # if self.masker_on:
            # Insert the target at a specific phase of the modulated masker
            masker_frequency = float(self.get_current_value('masker_frequency'))
            period = self.fs/masker_frequency
            phase_delay = self.get_current_value('phase_delay')/360.0*period
            phase = (offset % self.masker.shape[-1]) % period
            delay = phase_delay-phase
            if delay<0: delay+=period
            offset += int(delay)

            # Generate combined signal
            target_sf = 10.0**(-float(self.get_current_value('target_level'))/20.0)
            target_flat_duration = self.target_flat.shape[-1] / self.fs
            target_reps = round(self.get_current_value('target_duration')/target_flat_duration)
            target = [self.target_ramp[:-1], np.tile(self.target_flat, target_reps), -self.target_ramp[::-1]]
            target = np.concatenate(target) * target_sf
            if target.shape[-1] < self.fs: # If target is less than 1s
                target = np.concatenate([target, np.zeros(self.fs-target.shape[-1])])
            duration = target.shape[-1]
            masker = self.get_masker(offset, duration)
            signal = masker + target

            log.debug('Inserting target at %d', offset)
            log.debug('Overwriting %d samples in buffer', duration)

            self.engine.write_hw_ao(signal, offset)
            self.masker_offset = offset + duration
        except:
            log.error(sys.exc_info()[1])


    def target_toggle(self, info=None):
        try:
            ts = self.get_ts()
            log.debug('[target_toggle] at {}'.format(ts))
            ud = self.update_delay*1e-3 # Convert msec to sec
            offset = int(round((ts+ud)*self.fs))

            # Generate combined signal
            if self.target_on:
                self.target_on = False
                len = self.target_flat.shape[-1]
                pos = offset - self.target_ts
                rem = len - pos % len

                target = [self.get_target(pos, rem), -self.target_ramp[::-1]]
                target = np.concatenate(target)
                # Zero-pad if the target is less than 1 sec long
                if target.shape[-1] < self.fs:
                    target = np.concatenate(
                        [target, np.zeros(self.fs - target.shape[-1])]
                        )
            else:
                self.target_on = True
                # Start playing the target for 1 sec (fs samples)
                target = [self.target_ramp, self.get_target(0, self.fs)]
                target = np.concatenate(target)

            target_sf = 10.0**(-float(self.get_current_value('target_level'))/20.0)
            target = target * target_sf
            duration = target.shape[-1]
            self.target_ts = offset + self.target_ramp.shape[-1]
            self.target_offset = duration - self.target_ramp.shape[-1]
            self.masker_offset = offset + duration
            masker = self.get_masker(offset, duration)
            signal = masker + target

            log.debug('Inserting target start at %d', offset)
            log.debug('Overwriting %d samples in buffer', duration)
            # log.debug('Timestamp at insertion: %d', self.get_ts()*self.fs)

            self.engine.write_hw_ao(signal, offset)
        except:
            log.error(traceback.format_exc())

    def masker_update(self):
        # Get the current position in the analog output buffer, and add a cetain
        # update_delay (to give us time to generate and upload the new signal).
        ts = self.get_ts()
        ud = self.update_delay*1e-3 # Convert msec to sec
        offset = int(round((ts+ud)*self.fs))
        duration = self.fs
        signal = self.get_masker(offset, duration)
        try:
            self.engine.write_hw_ao(signal, offset)
            self.masker_offset = offset + duration
        except:
            log.error('[masker_update] Update delay %f is too small', ud)

    def masker_toggle(self, info=None):
        self.masker_on = not self.masker_on
        self.masker_update()

    def pump_toggle2(self, info=None):
        self.pump_override()

    def pump_trigger2(self, info=None):
        if not self.model.args.nopump:
            self.pump_trigger()

    def light_toggle(self, info=None):
        if self.light_on:
            self.engine.set_sw_do('light', 0)
            self.light_on = False
        else:
            self.engine.set_sw_do('light', 1)
            self.light_on = True

    def light_timeout(self, info=None):
        self.engine.set_sw_do('light', 0)
        self.light_on = False
        if hasattr(self, 'timer'): self.timer.cancel()
        self.start_timer('to_duration', Event.to_duration_elapsed)


    ############################################################################
    # Callback for buttons defined in the controller class
    ############################################################################

    def button_stage1(self, info=None):
        self.model.paradigm.button_target_play   = False
        self.model.paradigm.button_target_toggle = False
        self.model.paradigm.button_pump_trigger  = False
        self.model.paradigm.button_pump_toggle   = True
        self.model.paradigm.spout_target         = True
        self.model.paradigm.spout_pump_trigger   = False
        self.model.paradigm.spout_pump_toggle    = True
        self.model.paradigm.spout_after_button   = False
        self.model.paradigm.poke_target            = False


    def button_stage2(self, info=None):
        self.model.paradigm.button_target_play   = False
        self.model.paradigm.button_target_toggle = True
        self.model.paradigm.button_pump_trigger  = False
        self.model.paradigm.button_pump_toggle   = False
        self.model.paradigm.spout_target         = False
        self.model.paradigm.spout_pump_trigger   = True
        self.model.paradigm.spout_pump_toggle    = False
        self.model.paradigm.spout_after_button   = True
        self.model.paradigm.poke_target            = False


    ############################################################################
    # Callbacks for NI Engine
    ############################################################################

    def samples_acquired(self, names, samples):
        # Speaker in, mic, nose-poke IR, spout contact IR
        speaker, microphone, poke, spout = samples
        self.model.data.speaker.send(speaker)
        self.model.data.microphone.send(microphone)
        self.model.data.poke.send(poke)
        self.model.data.spout.send(spout)


    def samples_acquired2(self, names, samples):
        # self.model.data.ch1.send(samples[1])
        self.model.data.raw.send(samples)


    def samples_needed(self, names, offset, samples):
        if samples > 5*self.fs: samples = 5*self.fs
        signal = self.get_masker(self.masker_offset, samples)
        self.masker_offset += samples
        if self.target_on:
            target = self.get_target(self.target_offset, samples)
            target_sf = 10.0**(-float(self.get_current_value('target_level'))/20.0)
            target = target * target_sf
            signal += target
            self.target_offset += samples
        # log.debug('[samples_needed] samples  : %d', samples)
        # log.debug('[samples_needed] offset   : %d', offset)
        # if self.masker_offset != samples:
        #     log.debug('[samples_needed] timestamp: %d', self.get_ts()*self.fs)
        with self._lock:
            try:
                self.engine.write_hw_ao(signal)
            except:
                log.error(sys.exc_info()[1])

    event_map = {
        ('rising' , 'poke'    ): Event.poke_start      ,
        ('falling', 'poke'    ): Event.poke_end        ,
        ('rising' , 'spout' ): Event.spout_start   ,
        ('falling', 'spout' ): Event.spout_end     ,
        ('rising' , 'button'): Event.button_push   ,
        ('falling', 'button'): Event.button_release,
    }


    def di_changed(self, name, change, timestamp):
        # The timestamp is the number of analog output samples that have been
        # generated at the time the event occured. Convert to time in seconds
        # since experiment start.
        try:
            timestamp /= self.fs
            log.debug('detected {} edge on {} at {}'.format(change,name,timestamp))

            event = self.event_map[change, name]
            self.handle_event(event, timestamp)
        except:
            log.error(sys.exc_info()[1])


    def handle_event(self, event, timestamp=None):
        # Ensure that we don't attempt to process several events at the same
        # time. This essentially queues the events such that the next event
        # doesn't get processed until `_handle_event` finishes processing the
        # current one.

        # Only events generated by NI-DAQmx callbacks will have a timestamp.
        # Since we want all timing information to be in units of the analog
        # output sample clock, we will capture the value of the sample
        # clock if a timestamp is not provided. Since there will be some
        # delay between the time the event occurs and the time we read the
        # analog clock, the timestamp won't be super-accurate. However, it's
        # not super-important since these events are not reference points
        # around which we would do a perievent analysis. Important reference
        # points would include nose-poke initiation and withdraw, spout
        # contact, sound onset, lights on, lights off. These reference
        # points will be tracked via NI-DAQmx or can be calculated (i.e., we
        # know exactly when the target onset occurs because we precisely
        # specify the location of the target in the analog output buffer).

        with self._lock:
            if timestamp is None:
                timestamp = self.get_ts()
            self._handle_event(event, timestamp)
        # self.event_queue.put((event,timestamp))


    def _handle_event(self, event, timestamp):
        '''
        Give the current experiment state, process the appropriate response for
        the event that occured. Depending on the experiment state, a particular
        event may not be processed.
        '''
        self.model.data.log_event(timestamp, event.value)

        if self.state == 'paused':
            # TODO: Add hold duration
            if event == Event.poke_start:
                if self.get_current_value('poke_target'):
                    self.target_play()

            elif event == Event.spout_start:


                if not self.get_current_value('spout_after_button') or \
                        self.get_current_value('spout_after_button') and \
                        self.trial_state == TrialState.waiting_for_response:
                    if self.get_current_value('spout_after_button'):
                        self.trial_state = TrialState.waiting_for_poke_start
                        if hasattr(self, 'timer'): self.timer.cancel()
                    if self.get_current_value('spout_target'):
                        self.target_play()
                    if self.get_current_value('spout_pump_toggle'):
                        self.pump_override_on()
                    elif self.get_current_value('spout_pump_trigger'):
                        self.pump_trigger()

            elif event == Event.spout_end:
                if self.get_current_value('spout_pump_toggle'):
                    self.pump_override_off()

            elif event == Event.button_push:
                if self.get_current_value('button_target_play'):
                    self.target_play()
                elif self.get_current_value('button_target_toggle'):
                    self.target_toggle()
                if self.get_current_value('button_pump_toggle'):
                    self.pump_override_on()
                elif self.get_current_value('button_pump_trigger'):
                    self.pump_trigger()
                if self.get_current_value('spout_after_button'):
                    if self.trial_state == TrialState.waiting_for_response:
                        if hasattr(self, 'timer'): self.timer.cancel()
                    self.trial_state = TrialState.waiting_for_response

            elif event == Event.button_release:
                if self.get_current_value('button_target_toggle'):
                    self.target_toggle()
                if self.get_current_value('button_pump_toggle'):
                    self.pump_override_off()
                if self.get_current_value('spout_after_button'):
                    self.start_timer('response_duration',
                                     Event.response_duration_elapsed)

            elif event == Event.to_duration_elapsed:
                self.engine.set_sw_do('light', 1)
                self.light_on = True

            elif event == Event.response_duration_elapsed:
                self.trial_state = TrialState.waiting_for_poke_start

        else:
            if self.trial_state == TrialState.waiting_for_poke_start:
                if event == Event.poke_start:
                    # Animal has nose-poked in an attempt to initiate a trial.
                    self.trial_state = TrialState.waiting_for_poke_duration
                    self.start_timer('poke_duration', Event.poke_duration_elapsed)
                    # If the animal does not maintain the nose-poke long enough,
                    # this value will get overwritten with the next nose-poke.
                    # self.trial_info['poke_start'] = timestamp

            elif self.trial_state == TrialState.waiting_for_poke_duration:
                if event == Event.poke_end:
                    # Animal has withdrawn from nose-poke too early. Cancel the
                    # timer so that it does not fire a 'event_poke_duration_elapsed'.
                    log.debug('Animal withdrew too early')
                    self.timer.cancel()
                    self.trial_state = TrialState.waiting_for_poke_start
                elif event == Event.poke_duration_elapsed:
                    self.start_trial()

            elif self.trial_state == TrialState.waiting_for_hold_period:
                # All animal-initiated events (poke/spout) are ignored during this
                # period but we may choose to record the time of nose-poke withdraw
                # if it occurs.
                if event == Event.poke_end:
                    # Record the time of nose-poke withdrawal if it is the first
                    # time since initiating a trial.
                    log.debug('Animal withdrew during hold period')
                    # if 'poke_end' not in self.trial_info:
                    #     log.debug('Recording poke_end')
                    #     self.trial_info['poke_end'] = timestamp
                elif event == Event.hold_duration_elapsed:
                    self.trial_state = TrialState.waiting_for_response
                    self.start_timer('response_duration',
                                     Event.response_duration_elapsed)

            elif self.trial_state == TrialState.waiting_for_response:
                # If the animal happened to initiate a nose-poke during the hold
                # period above and is still maintaining the nose-poke, they have to
                # manually withdraw and re-poke for us to process the event.
                if event == Event.poke_end:
                    # Record the time of nose-poke withdrawal if it is the first
                    # time since initiating a trial.
                    log.debug('Animal withdrew during response period')
                    # if 'poke_end' not in self.trial_info:
                    #     self.trial_info['poke_end'] = timestamp
                elif event == Event.poke_start:
                    # self.trial_info['response_ts'] = timestamp
                    self.stop_trial(response='nose poke')
                elif event == Event.spout_start:
                    # self.trial_info['response_ts'] = timestamp
                    self.stop_trial(response='spout contact')
                elif event == Event.response_duration_elapsed:
                    # self.trial_info['response_ts'] = timestamp
                    self.stop_trial(response='no response')

            elif self.trial_state == TrialState.waiting_for_to:
                if event == Event.to_duration_elapsed:
                    # Turn the light back on
                    self.engine.set_sw_do('light', 1)
                    self.light_on = True
                    self.start_timer('iti_duration',
                                     Event.iti_duration_elapsed)
                    self.trial_state = TrialState.waiting_for_iti
                elif event in (Event.spout_start, Event.poke_start):
                    self.timer.cancel()
                    self.start_timer('to_duration', Event.to_duration_elapsed)

            elif self.trial_state == TrialState.waiting_for_iti:
                if event == Event.iti_duration_elapsed:
                    self.trial_state = TrialState.waiting_for_poke_start


    def start_timer(self, variable, event):
        # Even if the duration is 0, we should still create a timer because this
        # allows the `_handle_event` code to finish processing the event. The
        # timer will execute as soon as `_handle_event` finishes processing.
        duration = self.get_value(variable)
        self.timer = threading.Timer(duration, self.handle_event, [event])
        self.timer.start()

    def get_masker(self, offset, duration):
        masker_sf = 10.0**(-float(self.get_current_value('masker_level'))/20.0)
        if self.masker_on is False: masker_sf = 0;
        return self.get_cyclic(self.masker, offset, duration) * masker_sf

    def get_target(self, offset, duration):
        return self.get_cyclic(self.target_flat, offset, duration)

    def get_cyclic(self, signal, offset, duration):
        '''
        Get the next `duration` samples of the signal starting at `offset`. If
        reading past the end of the array, loop around to the beginning.
        '''
        size = signal.shape[-1]
        offset = offset % size
        result = []
        while True:
            if (offset+duration) < size:
                subset = signal[offset:offset+duration]
                duration = 0
            else:
                subset = signal[offset:]
                offset = 0
                duration = duration-subset.shape[-1]
            result.append(subset)
            if duration == 0:
                break
        return np.concatenate(result, axis=-1)

    def get_ts(self):
        return self.engine.ao_sample_clock()/self.fs


class Paradigm(
        PositiveCMRParadigmMixin,
        AbstractPositiveParadigm,
        # CLParadigmMixin,
        PositiveStage1Paradigm,
        PumpParadigmMixin,
        ):
    '''
    Defines the parameters required by the experiment (e.g. duration of various
    events, frequency of the stimulus, which speaker is active, etc.).
    '''
    kw = {'context':True, 'log':False}

    button_target_play   = Bool(False, label='Play Target'  , **kw)
    button_target_toggle = Bool(False, label='Toggle Target', **kw)
    button_pump_trigger  = Bool(False, label='Trigger Pump' , **kw)
    button_pump_toggle   = Bool(True , label='Toggle Pump'  , **kw)
    button_group = VGroup(
            'button_target_play',
            'button_target_toggle',
            'button_pump_trigger',
            'button_pump_toggle',
            label='Push Button',
            show_border=True,
            )

    spout_target       = Bool(True , label='Play Target' , **kw)
    spout_pump_trigger = Bool(False, label='Trigger Pump', **kw)
    spout_pump_toggle  = Bool(True , label='Toggle Pump' , **kw)
    spout_after_button = Bool(False, label='After Button', **kw)
    spout_group = VGroup(
            'spout_target',
            'spout_pump_trigger',
            'spout_pump_toggle',
            'spout_after_button',
            label='Lick Spout',
            show_border=True,
            )

    poke_target = Bool(False, label='Play Target', **kw)
    poke_group = VGroup(
        'poke_target',
        label='Nose Poke',
        show_border=True,
        )

    traits_view = View(
                VGroup(
                    #'go_probability',
                    HGroup(
                    Include('button_group'),
                    Include('spout_group'),
                    Include('poke_group')),
                    Include('constant_limits_paradigm_mixin_group'),
                    Include('abstract_positive_paradigm_group'),
                    Include('pump_paradigm_mixin_syringe_group'),
                    label='Paradigm',
                    ),
                VGroup(
                    # Note that because the Paradigm class inherits from
                    # PositiveCMRParadigmMixin all the parameters defined there are
                    # available as if they were defined on this class.
                    Include('speaker_group'),
                    'masker_filename',
                    'masker_level',
                    'target_filename',
                    'target_level',
                    'hw_att',
                    label='Sound',
                    ),
        )


class Data(PositiveData, PositiveCLDataMixin, PumpDataMixin):
    '''
    Container for the data
    '''
    pass


class Experiment(AbstractPositiveExperiment, CLExperimentMixin):
    '''
    Defines the GUI layout
    '''

    data = Instance(Data, ())
    paradigm = Instance(Paradigm, ())


node_name = 'PositiveCMRTraining'

'''
----------------------------------------------------------
Appetitive comodulation masking release (continuous noise)
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

import sys
import time
import json
import traceback
import threading
import Queue
from os import path

from traits.api import Instance, File, Any, Int, Float, Bool, String, on_trait_change
from traitsui.api import View, Include, VGroup, HGroup, Item
from pyface.api import error

from experiments.evaluate import Expression
from experiments.trial_setting import TrialSetting
from cns import get_config

# These mixins are shared with the positive_cmr_training paradigm.  I use the
# underscore so it's clear that these files do not define stand-alone paradigms.
from ._positive_cmr_mixin import PositiveCMRParadigmMixin
from ._positive_cmr_mixin import PositiveCMRControllerMixin

import numpy as np
from scipy.io import wavfile

# __name__ is a special variable available to the module that will be
# "paradigms.positive_cmr" (i.e. the "name" of the module as seen by Python).
import logging
log = logging.getLogger(__name__)

from experiments.abstract_experiment_controller  import AbstractExperimentController
from experiments.abstract_positive_experiment_v3 import AbstractPositiveExperiment
from experiments.abstract_positive_paradigm_v3   import AbstractPositiveParadigm
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
    waiting_for_poke_start         = 'waiting for nose poke start'
    waiting_for_poke_duration      = 'waiting for nose poke duration'
    waiting_for_poke_hold_duration = 'waiting for nose poke hold duration'
    waiting_for_hold_period        = 'waiting for hold period'
    waiting_for_response           = 'waiting for response'
    waiting_for_to                 = 'waiting for timeout'
    waiting_for_iti                = 'waiting for intertrial interval'


class Event(enum.Enum):
    '''
    Defines the possible events that may occur during the course of the
    experiment.

    This is specific to appetitive reinforcement paradigms.
    '''
    poke_start                 = 'initiated nose poke'
    poke_end                   = 'withdrew from nose poke'
    poke_duration_elapsed      = 'nose poke duration met'
    poke_hold_duration_elapsed = 'nose poke hold duration met'
    hold_duration_elapsed      = 'hold period over'
    response_duration_elapsed  = 'response timed out'
    spout_start                = 'spout contact'
    spout_end                  = 'withdrew from spout'
    to_duration_elapsed        = 'timeout over'
    iti_duration_elapsed       = 'ITI over'
    trial_start                = 'trial start'


class Controller(
        PositiveCMRControllerMixin,
        AbstractExperimentController,
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
    kw = {'context': True, 'log': True}
    update_delay = Float(200, **kw) # ms
    signal_level = Float(0  , **kw)

    thread = None
    thread_stop = False
    queue = Queue.Queue()

    def setup_experiment(self, info):
        self.model.data.setup()
        return

    def start_experiment(self, info):
        try:
            log.debug('Starting experiment')
            self.refresh_context()
            # Load the masker and target. Right now we assume that the nogo is
            # silent (i.e., a scaling factor of 0). Go trials will have a nonzero
            # scaling factor. In general, this is a fairly reasonable approximation
            # of SDT (i.e., the nogo should be some undetectable variant of the go,
            # right)?
            masker_filename = self.get_current_value('masker_filename')
            if not path.exists(masker_filename):
                m = 'Masker file {} does not exist'
                raise ValueError(m.format(masker_filename))
            self.masker_offset = 0
            masker_fs, masker = wavfile.read(masker_filename, mmap=True)
            self.masker = masker.astype('float64')
            sf = 1/np.sqrt(np.mean(self.masker**2))  # normalize by rms
            self.masker *= sf

            target_filename = self.get_current_value('target_filename')
            if not path.exists(target_filename):
                m = 'Go file {} does not exist'
                raise ValueError(m.format(target_filename))
            self.target_offset = 0
            target_fs, target = wavfile.read(target_filename, mmap=True)
            self.target = target.astype('float64')
            sf = 1/np.sqrt(np.mean(self.target**2)) # normalize by rms
            self.target *= sf

            if masker_fs <> target_fs:
                raise Exception('Masker and target sampling frequencies do not match')
            self.fs_ao = masker_fs

            # Scale both signals to prevent output saturation with 0 dB attenuation
            signal_max = max(abs(self.masker)) + max(abs(self.target))
            self.masker *= 10/signal_max
            self.target *= 10/signal_max
            # Store the scaling value in the current context in order to get logged
            signal_level = 20*np.log10(10/(signal_max))
            signal_level = np.floor(self.signal_level*10)/10
            self.set_current_value('signal_level', signal_level)

            self.trial_state = TrialState.waiting_for_poke_start

            if self.model.args.sim:
                import daqengine.sim
                self.engine = daqengine.sim.Engine()
            else:
                import daqengine.ni
                self.engine = daqengine.ni.Engine()

            if self.model.spool_physiology:
                self.physiology_handler.start_physiology()

            # Nose poke and spout contact TTL. If we want to monitor additional
            # events occuring in the behavior booth (e.g., room light on/off), we
            # can connect the output controlling the light/pump to an input and
            # monitor state changes on that input.
            self.engine.configure_hw_di(self.fs_ao, '/dev1/port0/line1:2',
                                        clock='/dev1/ctr1', names=['spout', 'poke'],
                                        start_trigger='/dev1/ao/starttrigger')

            # Speaker in, mic, nose-poke IR, spout contact IR. Not everything will
            # necessarily be connected.
            self.fs_ai = 250e3/4
            self.engine.configure_hw_ai(self.fs_ai, '/dev1/ai0:3', (-10, 10),
                                        names=['speaker', 'mic', 'poke', 'spout'],
                                        start_trigger='/dev1/ao/starttrigger',
                                        timebase_src='/dev1/20mhztimebase',
                                        timebase_rate=20e6)

            # Speaker out
            # The AO task on dev1 is considered as the master task
            self.engine.configure_hw_ao(self.fs_ao, '/dev1/ao0', (-10, 10),
                                        names=['speaker'],
                                        timebase_src='/dev1/20mhztimebase',
                                        timebase_rate=20e6)

            # Control for room light
            self.engine.configure_sw_do('/dev1/port1/line1', names=['light'])
            self.engine.set_sw_do('light', 1)

            self.engine.register_ao_callback(self.samples_needed)
            self.engine.register_ai_callback(self.samples_acquired)
            self.engine.register_di_change_callback(self.di_changed,
                                                    debounce=self.fs_ao*50e-3)

            self.model.data.speaker.fs = self.fs_ai
            self.model.data.mic.fs     = self.fs_ai
            self.model.data.poke.fs    = self.fs_ai
            self.model.data.spout.fs   = self.fs_ai

            # Configure the pump
            if not self.model.args.nopump:
                self.iface_pump.set_direction('infuse')

            # Generate a random seed based on the computer's clock.
            self.random_seed = int(time.time())

            self.random_generator = np.random.RandomState(self.random_seed)

            node = info.object.experiment_node
            node._v_attrs['trial_sequence_random_seed'] = self.random_seed

            self.state = 'running'

            self.engine.start()
            self.thread = threading.Thread(target=self.thread_loop, args=[])
            self.thread.start()
            self.trigger_next()

            if self.engine.ai_sample_clock_rate() <> self.fs_ai:
                raise Exception('The requested analog input sampling rate ' + \
                    'couldn\'t be accurately generated, please use a rate ' + \
                    'divisable by 100 MHz.')
            if self.engine.ao_sample_clock_rate() <> self.fs_ao:
                raise Exception('The requested analog output sampling rate ' + \
                    'couldn''t be accurately generated, please use a rate ' + \
                    'divisable by 100 MHz.')
        except:
            log.error(traceback.format_exc())
            raise

    def trigger_next(self):
        log.debug('Triggering next trial')
        c_nogo = 0
        trial_log = self.model.data.trial_log
        while len(trial_log)-c_nogo-1 > 0:
            if trial_log.ttype.values[len(trial_log)-c_nogo-1] in ('NOGO', 'NOGO_REPEAT'):
                c_nogo += 1
            else:
                break
        self.model.data.c_nogo = c_nogo

        self.trial_info = {}
        self.refresh_context()
        self.current_setting = self.next_setting()
        self.evaluate_pending_expressions(self.current_setting)
        self.model.data.trial_type = self.get_current_value('ttype')

    def log_trial(self, **kwargs):
        # HDF5 data files do not natively support unicode strings so we need to
        # convert our filename to an ASCII string.  While we're at it, we should
        # probably strip the directory path as well and just save the basename.
        log.debug('Logging trial epoch to HDF5')
        self.model.data.trial_epoch.send([(
            self.trial_info['poke_start'], self.trial_info['response_ts']
        )])
        target_filename = self.get_current_value('target_filename')
        kwargs['target_filename'] = str(path.basename(target_filename))
        masker_filename = self.get_current_value('masker_filename')
        kwargs['masker_filename'] = str(path.basename(masker_filename))
        super(Controller, self).log_trial(**kwargs)

    def stop_experiment(self, info):
        log.debug('Stopping experiment')
        self.thread_stop = True
        self.thread.join()
        if not self.model.args.nopump:
            self.iface_pump.disconnect()
        self.engine.stop()

    def remind(self, info=None):
        # If trial is already running, the remind will be presented on the next
        # trial.
        self.remind_requested = True
        if self.trial_state == TrialState.waiting_for_poke_start:
            self.trigger_next()

    def cancel_remind(self, info=None):
        self.remind_requested = False

    def pause(self, info=None):
        # if self.model.args.nopump:
            if self.trial_state == TrialState.waiting_for_poke_start:
                self.handle_event(Event.poke_start)
            else:
                self.handle_event(Event.spout_start)

    def start_trial(self):
        log.debug('Starting trial: %s', self.get_current_value('ttype'))

        self.target_play()

        # TODO - the hold duration will include the update delay. Do we need
        # super-precise tracking of hold period or can it vary by a couple 10s
        # to 100s of msec?
        self.trial_state = TrialState.waiting_for_hold_period
        self.start_timer('hold_duration', Event.hold_duration_elapsed)

    def stop_trial(self, response):
        log.debug('Stopping trial')

        trial_type = self.get_current_value('ttype')
        if response != 'no response' and 'target_start' in self.trial_info:
            self.trial_info['response_time'] = \
                self.trial_info['response_ts']-self.trial_info['target_start']
        else:
            self.trial_info['response_time'] = np.nan

        self.trial_info['reaction_time'] = \
            self.trial_info.get('poke_end', np.nan)-self.trial_info['poke_start']

        if trial_type in ('GO', 'GO_REMIND'):
            score = 'HIT' if response == 'spout contact' else 'MISS'
        elif trial_type in ('NOGO', 'NOGO_REPEAT'):
            score = 'FA' if response == 'spout contact' else 'CR'

        log.debug('Score is %s', score)

        if score == 'FA':
            # Turn the light off
            log.debug('Entering timeout')
            self.engine.set_sw_do('light', 0)
            self.start_timer('to_duration', Event.to_duration_elapsed)
            self.trial_state = TrialState.waiting_for_to
        else:
            if score == 'HIT':
                # TODO: Investigate why are changes to reward_volume applied on
                # the second trial rather than the first one?
                log.debug('Trigerring pump')
                if not self.model.args.nopump:
                    # TODO: check if removing this line is okay or not
                    self.set_pump_volume(self.get_current_value('reward_volume'))
                    self.pump_trigger([])
                else:
                    log.debug('Pump not triggered in "-nopump" mode')
                ts = self.get_ts()
                pump_duration = self.get_current_value('reward_volume') / 1e3 \
                    / self.get_current_value('pump_rate') * 60
                log.debug('Logging pump epoch to HDF5')
                self.model.data.pump_epoch.send([(ts, ts+pump_duration)])

            log.debug('Entering intertrial interval')
            self.trial_state = TrialState.waiting_for_iti
            self.start_timer('iti_duration', Event.iti_duration_elapsed)

        # Overrwrite output buffer with the masker to stop sound
        # ts = self.get_ts()
        # ud = self.get_current_value('update_delay')*1e-3 # Convert msec to sec
        # offset = int(round((ts+ud)*self.fs_ao))
        # duration = self.get_target().shape[-1]
        # masker_sf = 10.0**(-float(self.get_current_value('masker_level'))/20.0)
        # signal = self.get_masker(offset, duration) * masker_sf
        # try:
        #     self.engine.write_hw_ao(signal, offset)
        #     self.masker_offset = offset + duration
        # except:
        #     log.error('[stop_trial] Update delay %f is too small', ud)

        self.log_trial(score=score, response=response, ttype=trial_type,
                       **self.trial_info)
        self.trigger_next()

    def context_updated(self):
        if self.trial_state == TrialState.waiting_for_poke_start:
            self.trigger_next()

    def target_play(self, info=None):
        try:
            log.debug('Initializing target')
            # Get the current position in the analog output buffer, and add a cetain
            # update_delay (to give us time to generate and upload the new signal).
            ts = self.get_ts()
            ud = self.update_delay*1e-3 # Convert msec to sec
            offset = int(round((ts+ud)*self.fs_ao))

            # Insert the target at a specific phase of the modulated masker
            masker_frequency = self.get_current_value('masker_frequency')
            if masker_frequency <> 0:
                period = self.fs_ao/masker_frequency
                phase_delay = self.get_current_value('phase_delay')/360.0*period
                phase = (offset % self.masker.shape[-1]) % period
                delay = phase_delay-phase
                if delay<0: delay+=period
                offset += int(delay)

            # Generate combined signal
            target_level = self.get_current_value('target_level')
            if target_level < 0: target_level = 0
            target_sf = 10.0**(-target_level/20.0)
            target_duration = self.target.shape[-1] / self.fs_ao
            target_reps = round(self.get_current_value('target_duration')/target_duration)
            target_reps = int(target_reps)
            target = np.tile(self.target, target_reps) * target_sf
            if target.shape[-1] < self.fs_ao: # Zero-pad if target is less than 1s
                target = np.concatenate([target, np.zeros(self.fs_ao-target.shape[-1])])
            # Ramp beginning and end of the target
            target_ramp_length = self.get_current_value('target_ramp_duration') * 1e-3 * self.fs_ao
            target_ramp_length = int(target_ramp_length)
            if target_ramp_length <> 0:
                target_ramp = np.sin(2*np.pi*1/target_ramp_length/4*np.arange(target_ramp_length))**2
                target[0:target_ramp_length]      *= target_ramp
                target[:-target_ramp_length-1:-1] *= target_ramp
            duration = target.shape[-1]
            masker = self.get_masker(offset, duration)
            signal = masker + target

            log.debug('Inserting target at %d', offset)
            log.debug('Overwriting %d samples in buffer', duration)
            self.engine.write_hw_ao(signal, offset)
            self.masker_offset = offset + duration

            log.debug('Logging target epoch to HDF5')
            target_end = ts + self.get_current_value('target_duration')
            self.trial_info['target_start'] = ts
            self.trial_info['target_end'] = target_end
            self.model.data.target_epoch.send([(ts, target_end)])

        except:
            log.error(traceback.format_exc())

    ############################################################################
    # Callbacks for NI Engine
    ############################################################################
    def samples_acquired(self, names, samples):
        # Speaker in, mic, nose-poke IR, spout contact IR
        speaker, mic, poke, spout = samples
        self.model.data.speaker.send(speaker)
        self.model.data.mic.send(mic)
        self.model.data.poke.send(poke)
        self.model.data.spout.send(spout)

    def samples_needed(self, names, offset, samples):
        if samples > 5*self.fs_ao: samples = 5*self.fs_ao
        signal = self.get_masker(self.masker_offset, samples)
        self.masker_offset += samples
        # if self.target_on:
        #     signal += self.get_target(self.target_offset, samples)
        #     self.target_offset += samples
        # log.debug('[samples_needed] samples  : %d', samples)
        # log.debug('[samples_needed] offset   : %d', offset)
        # if self.masker_offset != samples:
        #     log.debug('[samples_needed] timestamp: %d', self.get_ts()*self.fs_ao)
        # with self._lock:
        try:
            self.engine.write_hw_ao(signal)
        except:
            log.error(traceback.format_exc())

    event_map = {
        ('rising' , 'poke' ): Event.poke_start ,
        ('falling', 'poke' ): Event.poke_end   ,
        ('rising' , 'spout'): Event.spout_start,
        ('falling', 'spout'): Event.spout_end  ,
    }

    def di_changed(self, name, change, timestamp):
        # The timestamp is the number of analog output samples that have been
        # generated at the time the event occured. Convert to time in seconds
        # since experiment start.
        timestamp /= self.fs_ao
        log.debug('Detected {} edge on {} at {}'.format(change, name,timestamp))
        event = self.event_map[change, name]
        self.handle_event(event, timestamp)

    def thread_loop(self):
        pump_ts = 0

        while not self.thread_stop:
            try:
                if not self.queue.empty():
                    log.debug('Fetching from queue')
                    (event, timestamp) = self.queue.get()
                    log.debug('Fetched event %s at %f from the queue', event, timestamp)
                    self._handle_event(event, timestamp)

                # Monitor pump for changes in infused volume every 0.5s
                # This will update the data.water_infused variable and also
                # log the current volume along with its timestamp in HDF5
                ts = self.get_ts()
                if ts-pump_ts >= .5:
                    log.debug('Monitoring pump')
                    pump_ts = ts
                    if not self.model.args.nopump:
                        self.monitor_pump()
                    log.debug('Pump monitored')
            except:
                log.error(traceback.format_exc())
            time.sleep(.001) # 1 ms

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
        try:
            if timestamp is None: timestamp = self.get_ts()

            log.debug('Adding event %s at %f to the queue', event, timestamp)
            self.queue.put((event, timestamp))
            log.debug('Event added to queue')
        except:
            log.error(traceback.format_exc())

    poke_start_ts  = np.nan
    spout_start_ts = np.nan

    def _handle_event(self, event, timestamp):
        '''
        Give the current experiment state, process the appropriate response for
        the event that occured. Depending on the experiment state, a particular
        event may not be processed.
        '''
        self.model.data.log_event(timestamp, event.value)

        if event == Event.poke_start:
            if self.poke_start_ts is not np.nan:
                log.debug('Logging poke epoch to HDF5')
                self.model.data.poke_epoch.send([(self.poke_start_ts, np.nan)])
            self.poke_start_ts = timestamp
        elif event == Event.poke_end:
            log.debug('Logging poke epoch to HDF5')
            self.model.data.poke_epoch.send([(self.poke_start_ts, timestamp)])
            self.poke_start_ts = np.nan
        elif event == Event.spout_start:
            if self.spout_start_ts is not np.nan:
                log.debug('Logging spout epoch to HDF5')
                self.model.data.spout_epoch.send([(self.spout_start_ts, np.nan)])
            self.spout_start_ts = timestamp
        elif event == Event.spout_end:
            log.debug('Logging spout epoch to HDF5')
            self.model.data.spout_epoch.send([(self.spout_start_ts, timestamp)])
            self.spout_start_ts = np.nan

        log.debug('Handling %s in %s', event, self.trial_state)

        if self.trial_state == TrialState.waiting_for_poke_start:
            if event == Event.poke_start:
                # Animal has nose-poked in an attempt to initiate a trial.
                self.trial_state = TrialState.waiting_for_poke_duration
                self.start_timer('poke_duration', Event.poke_duration_elapsed)
                # If the animal does not maintain the nose-poke long enough,
                # this value will get overwritten with the next nose-poke.
                self.trial_info['poke_start'] = timestamp

        elif self.trial_state == TrialState.waiting_for_poke_duration:
            if event == Event.poke_end:
                # Animal has withdrawn from nose-poke too early. Cancel the
                # timer so that it does not fire a 'event_poke_duration_elapsed'.
                log.debug('Animal withdrew too early')
                self.timer.cancel()
                self.trial_state = TrialState.waiting_for_poke_start
            elif event == Event.poke_duration_elapsed:
                if self.get_current_value('poke_hold_duration') <= 0 \
                    or self.get_current_value('ttype') in ('NOGO', 'NOGO_REPEAT'):
                    self.start_trial()
                else:
                    log.debug('Starting trial: %s', self.get_current_value('ttype'))
                    self.target_play()
                    self.trial_state = TrialState.waiting_for_poke_hold_duration
                    self.start_timer('poke_hold_duration', Event.poke_hold_duration_elapsed)

        elif self.trial_state == TrialState.waiting_for_poke_hold_duration:
            if event == Event.poke_end:
                log.debug('Animal withdrew too early during poke hold period')
                log.debug('Trial canceled')
                self.timer.cancel()
                self.trial_state = TrialState.waiting_for_poke_start
            elif event == Event.poke_hold_duration_elapsed:
                self.trial_state = TrialState.waiting_for_hold_period
                self.start_timer('hold_duration', Event.hold_duration_elapsed)

        elif self.trial_state == TrialState.waiting_for_hold_period:
            # All animal-initiated events (poke/spout) are ignored during this
            # period but we may choose to record the time of nose-poke withdraw
            # if it occurs.
            if event == Event.poke_end:
                # Record the time of nose-poke withdrawal if it is the first
                # time since initiating a trial.
                log.debug('Animal withdrew during hold period')
                if 'poke_end' not in self.trial_info:
                    log.debug('Recording poke_end')
                    self.trial_info['poke_end'] = timestamp
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
                # self.start_timer('response_duration',
                #                  Event.response_duration_elapsed)
                if 'poke_end' not in self.trial_info:
                    self.trial_info['poke_end'] = timestamp
            elif event == Event.poke_start:
                self.timer.cancel();
                self.trial_info['response_ts'] = timestamp
                self.stop_trial(response='nose poke')
            elif event == Event.spout_start:
                self.timer.cancel();
                self.trial_info['spout_start'] = timestamp
                self.trial_info['response_ts'] = timestamp
                self.stop_trial(response='spout contact')
            # elif event == Event.spout_end:
            #     pass
            elif event == Event.response_duration_elapsed:
                self.timer.cancel();
                self.trial_info['response_ts'] = timestamp
                self.stop_trial(response='no response')

        elif self.trial_state == TrialState.waiting_for_to:
            if event == Event.to_duration_elapsed:
                # Turn the light back on
                self.engine.set_sw_do('light', 1)
                self.start_timer('iti_duration',
                                 Event.iti_duration_elapsed)
                self.trial_state = TrialState.waiting_for_iti
            elif event in (Event.spout_start, Event.poke_start):
                self.timer.cancel()
                self.start_timer('to_duration', Event.to_duration_elapsed)

        elif self.trial_state == TrialState.waiting_for_iti:
            if event == Event.iti_duration_elapsed:
                self.trial_state = TrialState.waiting_for_poke_start

        log.debug('Event handled')

    def start_timer(self, variable, event):
        # Even if the duration is 0, we should still create a timer because this
        # allows the `_handle_event` code to finish processing the event. The
        # timer will execute as soon as `_handle_event` finishes processing.
        duration = self.get_value(variable)
        self.timer = threading.Timer(duration, self.handle_event, [event])
        self.timer.start()

    def get_ts(self):
        return self.engine.ao_sample_clock()/self.fs_ao

    # Track changes in the trial settings tabulator (usually for target_level)
    @on_trait_change('model.paradigm.+container*.+context, +context')
    def trait_change(self, instance, name, old, new):
        if type(instance) is TrialSetting and name in ('masker_level','target_level'):
            self.check_level(new)

    def set_masker_level(self, level):
        self.check_level(level)

    def set_target_level(self, level):
        self.check_level(level)

    # Only inform the user that the entered value is not allowed. The context
    # target and masker levels will not be changed, however, when outputting the
    # sounds the level limit is applied
    def check_level(self, level):
        try:
            if level < 0:
                msg = 'Negative masker or target attenuation values are not allowed.\nWill use 0 dB instead.'
                error(self.info.ui.control, message=msg, title='Error applying changes')
                # log.error(msg)
        except:
            log.error(traceback.format_exc())

    def get_masker(self, offset, duration):
        masker_level = self.get_current_value('masker_level')
        if masker_level < 0: masker_level = 0
        masker_sf = 10.0**(-masker_level/20.0)
        return self.get_cyclic(self.masker, offset, duration) * masker_sf

    def get_target(self, offset, duration):
        target_level = self.get_current_value('target_level')
        if target_level < 0: target_level = 0
        target_sf = 10.0**(-target_level/20.0)
        return self.get_cyclic(self.target, offset, duration) * target_sf

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
        return self.engine.ao_sample_clock()/self.fs_ao

class Paradigm(
        PositiveCMRParadigmMixin,
        AbstractPositiveParadigm,
        CLParadigmMixin,
        PumpParadigmMixin,
        ):
    '''
    Defines the parameters required by the experiment (e.g. duration of various
    events, frequency of the stimulus, which speaker is active, etc.).
    '''

    # Parameters specific to the actual appetitive paradigm that are not needed
    # by the training program (and therefore not in the "mixin")
    traits_view = View(
            VGroup(
                #'go_probability',
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
                'masker_frequency',
                'target_filename',
                'target_level',
                'target_ramp_duration',
                'hw_att',
                label='Sound',
                ),
            )


class Data(PositiveData, PositiveCLDataMixin, PumpDataMixin):
    '''
    Container for the data
    '''
    c_nogo = Int(0, context=True, label='Consecutive nogos (including repeats)')
    trial_type = String('GO_REMIND', context=True, label='Upcoming trial')
    pass


class Experiment(AbstractPositiveExperiment, CLExperimentMixin):
    '''
    Defines the GUI layout
    '''

    data = Instance(Data, ())
    paradigm = Instance(Paradigm, ())

    experiment_summary_group = VGroup(
        'object.data.trial_type',
        'object.data.water_infused',
        label='Experiment Summary',
        style='readonly',
        show_border=True,
        )

node_name = 'PositiveCMR'

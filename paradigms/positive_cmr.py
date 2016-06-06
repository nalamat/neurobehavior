'''
Appetitive comodulation masking release (continuous noise)
----------------------------------------------------------
:Authors: **Brad Buran <bburan@alum.mit.edu>**
          **Antje Ihlefeld <ai33@nyu.edu>**

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

from os import path

from traits.api import Instance, File, Any, Int, Bool
from traitsui.api import View, Include, VGroup

from experiments.evaluate import Expression

from cns import get_config
from time import time

# These mixins are shared with the positive_cmr_training paradigm.  I use the
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

from experiments.abstract_experiment_controller import AbstractExperimentController
from experiments.abstract_positive_experiment_v3 import AbstractPositiveExperiment
from experiments.abstract_positive_paradigm_v3 import AbstractPositiveParadigm
from experiments.positive_data_v3 import PositiveData

from experiments.pump_controller_mixin import PumpControllerMixin
from experiments.pump_paradigm_mixin import PumpParadigmMixin
from experiments.pump_data_mixin import PumpDataMixin

from experiments.cl_controller_mixin import CLControllerMixin
from experiments.cl_paradigm_mixin import CLParadigmMixin
from experiments.cl_experiment_mixin import CLExperimentMixin
from experiments.positive_cl_data_mixin import PositiveCLDataMixin


class TrialState(enum.Enum):
    '''
    Defines the possible states that the experiment can be in. We use an Enum to
    minimize problems that arise from typos by the programmer (e.g., they may
    accidentally set the state to "waiting_for_nose_poke_start" rather than
    "waiting_for_np_start").

    This is specific to appetitive reinforcement paradigms.
    '''
    waiting_for_np_start = 'waiting for nose-poke start'
    waiting_for_np_duration = 'waiting for nose-poke duration'
    waiting_for_hold_period = 'waiting for hold period'
    waiting_for_response = 'waiting for response'
    waiting_for_to = 'waiting for timeout'
    waiting_for_iti = 'waiting for intertrial interval'


class Event(enum.Enum):
    '''
    Defines the possible events that may occur during the course of the
    experiment.

    This is specific to appetitive reinforcement paradigms.
    '''
    np_start = 'initiated nose poke'
    np_end = 'withdrew from nose poke'
    np_duration_elapsed = 'nose poke duration met'
    hold_duration_elapsed = 'hold period over'
    response_duration_elapsed = 'response timed out'
    spout_start = 'spout contact'
    spout_end = 'withdrew from spout'
    to_duration_elapsed = 'timeout over'
    iti_duration_elapsed = 'ITI over'
    trial_start = 'trial start'


class Controller(
        PositiveCMRControllerMixin,
        AbstractExperimentController,
        CLControllerMixin,
        PumpControllerMixin,
        ):
    '''
    Controls experiment logic (i.e. communicates with the TDT hardware,
    responds to input by the user, etc.).
    '''
    random_generator = Any
    random_seed = Int
    remind_requested = Bool

    # Track the current state of the experiment. How the controller responds to
    # events will depend on the state.
    trial_state = Instance(TrialState, TrialState.waiting_for_np_start)

    def _get_status(self):
        return self.trial_state.value

    preload_samples = 200000*5
    update_delay = 100000

    _lock = threading.Lock()
    engine = Instance('daqengine.ni.Engine')

    fs = 100e3

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
        test_sf = 10.0**(self.get_current_value('test_att')/-20.0)
        
        masker_filename = self.get_current_value('masker_filename')
        if not path.exists(masker_filename):
            m = 'Masker file {} does not exist'
            raise ValueError(m.format(masker_filename))
        self.masker_offset = 0
        self.fs, masker = wavfile.read(masker_filename, mmap=True)
        self.masker = masker.astype('float64')/np.iinfo(np.int16).max * test_sf
        
        self.update_delay = int(self.fs * 150e-3) # 50ms

        target_filename = self.get_current_value('target_filename')
        if not path.exists(target_filename):
            m = 'Go file {} does not exist'
            raise ValueError(m.format(target_filename))
        self.target_offset = 0
        self.fs, target = wavfile.read(target_filename, mmap=True)
        self.target = target.astype('float64')/np.iinfo(np.int16).max * test_sf

        self.trial_state = TrialState.waiting_for_np_start
        self.engine = Engine()

        # Speaker in, mic, nose-poke IR, spout contact IR. Not everything will
        # necessarily be connected.
        self.engine.configure_hw_ai(self.fs/100, 'Dev2/ai0:3', (-10, 10))

        # Speaker out
        self.engine.configure_hw_ao(self.fs, 'Dev2/ao0', (-10, 10))

        # Nose poke and spout contact TTL. If we want to monitor additional
        # events occuring in the behavior booth (e.g., room light on/off), we
        # can connect the output controlling the light/pump to an input and
        # monitor state changes on that input.
        self.engine.configure_et('/Dev2/port0/line1:2', 'ao/SampleClock',
                                 names=['spout', 'np'])

        # Control for pump and room light
        self.engine.configure_sw_do('/Dev2/port1/line1',
                                    names=['light'])
        self.engine.register_ao_callback(self.samples_needed)
        self.engine.register_ai_callback(self.samples_acquired)
        self.engine.register_et_callback(self.et_fired)

        self.model.data.microphone.fs = self.fs

        # Configure the pump
        self.iface_pump.set_direction('infuse')

        # Generate a random seed based on the computer's clock.
        self.random_seed = int(time())

        self.random_generator = np.random.RandomState(self.random_seed)

        node = info.object.experiment_node
        node._v_attrs['trial_sequence_random_seed'] = self.random_seed

        self.samples_needed(self.preload_samples)

        self.state = 'running'
        self.engine.start()
        self.trigger_next()

    def trigger_next(self):
        self.trial_info = {}
        self.invalidate_context()
        self.current_setting = self.next_setting()
        self.evaluate_pending_expressions(self.current_setting)

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

    def request_remind(self, info=None):
        # If trial is already running, the remind will be presented on the next
        # trial.
        self.remind_requested = True

    def start_trial(self):
        # Get the current position in the analog output buffer, and add a cetain
        # update_delay (to give us time to generate and upload the new signal).
        ts = self.get_ts()
        offset = int(round(ts*self.fs)) + self.update_delay
        
        #### Insert target within a specific phase of the periodic masker
        masker_frequency = self.get_current_value('masker_frequency')
        period = self.fs/masker_frequency
        phase_delay = self.get_current_value('phase_delay')/360.0*period
        phase = (offset % self.masker.shape[-1]) % period
        delay = phase-phase_delay
        if delay<0: delay+=period
        offset += int(delay);
        ####
        
        log.debug('Inserting target at %d', offset)
        # TODO - should be able to calculate a precise duration.
        duration = self.engine.ao_write_space_available(offset)/10
        log.debug('Overwriting %d samples in buffer', duration)

        masker_sf = 10.0**(-self.get_current_value('masker_level')/20.0)
        target_sf = 10.0**(-self.get_current_value('target_level')/20.0)

        # Generate combined signal
        signal = self.get_masker(offset, duration) * masker_sf
        target = self.get_target() * target_sf
        
        signal[:target.shape[-1]] += target
        self.engine.write_hw_ao(signal, offset)
        self._masker_offset = offset + signal.shape[-1]
            
        # TODO - the hold duration will include the update delay. Do we need
        # super-precise tracking of hold period or can it vary by a couple 10s
        # to 100s of msec?
        self.trial_state = TrialState.waiting_for_hold_period
        self.start_timer('hold_duration', Event.hold_duration_elapsed)
        self.trial_info['target_start'] = ts
        self.trial_info['target_end'] = ts+duration/self.fs

    def stop_trial(self, response):
        trial_type = self.get_current_value('ttype')
        if response != 'no response':
            self.trial_info['response_time'] = \
                self.trial_info['response_ts']-self.trial_info['target_start']
        else:
            self.trial_info['response_time'] = np.nan

        self.trial_info['reaction_time'] = \
            self.trial_info.get('np_end', np.nan)-self.trial_info['np_start']

        if trial_type in ('GO', 'GO_REMIND'):
            score = 'HIT' if response == 'spout contact' else 'MISS'
        elif trial_type in ('NOGO', 'NOGO_REPEAT'):
            score = 'FA' if response == 'spout contact' else 'CR'

        if score == 'FA':
            # Turn the light off
            self.engine.set_sw_do('light', 0)
            self.start_timer('to_duration', Event.to_duration_elapsed)
            self.trial_state = TrialState.waiting_for_to
        else:
            if score == 'HIT':
                # TODO: Investigate why are changes to reward_volume applied on
                # the second trial rather than the first one?
                self.set_pump_volume(self.get_current_value('reward_volume'))
                self.pump_trigger([])
                
            self.start_timer('iti_duration', Event.iti_duration_elapsed)
            self.trial_state = TrialState.waiting_for_iti

        print(self.trial_info)
        self.log_trial(score=score, response=response, ttype=trial_type,
                       **self.trial_info)
        self.trigger_next()

    ############################################################################
    # Callbacks for NI Engine
    ############################################################################
    def samples_acquired(self, samples):
        # Speaker in, mic, nose-poke IR, spout contact IR
        speaker, mic, np, spout = samples
        self.model.data.microphone.send(speaker)

    def samples_needed(self, samples):
        masker = self.get_masker(self.masker_offset, samples)
        self.engine.write_hw_ao(masker)
        self.masker_offset += samples

    event_map = {
        ('rising', 'np'): Event.np_start,
        ('falling', 'np'): Event.np_end,
        ('rising', 'spout'): Event.spout_start,
        ('falling', 'spout'): Event.spout_end,
    }

    def et_fired(self, edge, line, timestamp):
        # The timestamp is the number of analog output samples that have been
        # generated at the time the event occured. Convert to time in seconds
        # since experiment start.
        timestamp /= self.fs
        log.debug('detected {} edge on {} at {}'.format(edge, line, timestamp))
        event = self.event_map[edge, line]
        self.handle_event(event, timestamp)

    def handle_event(self, event, timestamp=None):
        # Ensure that we don't attempt to process several events at the same
        # time. This essentially queues the events such that the next event
        # doesn't get processed until `_handle_event` finishes processing the
        # current one.
        with self._lock:
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
            if timestamp is None:
                timestamp = self.get_ts()
            self._handle_event(event, timestamp)

    def _handle_event(self, event, timestamp):
        '''
        Give the current experiment state, process the appropriate response for
        the event that occured. Depending on the experiment state, a particular
        event may not be processed.
        '''
        self.model.data.log_event(timestamp, event.value)

        if self.trial_state == TrialState.waiting_for_np_start:
            if event == Event.np_start:
                # Animal has nose-poked in an attempt to initiate a trial.
                self.trial_state = TrialState.waiting_for_np_duration
                self.start_timer('np_duration', Event.np_duration_elapsed)
                # If the animal does not maintain the nose-poke long enough,
                # this value will get overwritten with the next nose-poke.
                self.trial_info['np_start'] = timestamp

        elif self.trial_state == TrialState.waiting_for_np_duration:
            if event == Event.np_end:
                # Animal has withdrawn from nose-poke too early. Cancel the
                # timer so that it does not fire a 'event_np_duration_elapsed'.
                log.debug('Animal withdrew too early')
                self.timer.cancel()
                self.trial_state = TrialState.waiting_for_np_start
            elif event == Event.np_duration_elapsed:
                self.start_trial()

        elif self.trial_state == TrialState.waiting_for_hold_period:
            # All animal-initiated events (poke/spout) are ignored during this
            # period but we may choose to record the time of nose-poke withdraw
            # if it occurs.
            if event == Event.np_end:
                # Record the time of nose-poke withdrawal if it is the first
                # time since initiating a trial.
                log.debug('Animal withdrew during hold period')
                if 'np_end' not in self.trial_info:
                    log.debug('Recording np_end')
                    self.trial_info['np_end'] = timestamp
            elif event == Event.hold_duration_elapsed:
                self.trial_state = TrialState.waiting_for_response
                self.start_timer('response_duration',
                                 Event.response_duration_elapsed)

        elif self.trial_state == TrialState.waiting_for_response:
            # If the animal happened to initiate a nose-poke during the hold
            # period above and is still maintaining the nose-poke, they have to
            # manually withdraw and re-poke for us to process the event.
            if event == Event.np_end:
                # Record the time of nose-poke withdrawal if it is the first
                # time since initiating a trial.
                log.debug('Animal withdrew during response period')
                if 'np_end' not in self.trial_info:
                    self.trial_info['np_end'] = timestamp
            elif event == Event.np_start:
                self.trial_info['response_ts'] = timestamp
                self.stop_trial(response='nose poke')
            elif event == Event.spout_start:
                self.trial_info['response_ts'] = timestamp
                self.stop_trial(response='spout contact')
            elif event == Event.response_duration_elapsed:
                self.trial_info['response_ts'] = timestamp
                self.stop_trial(response='no response')

        elif self.trial_state == TrialState.waiting_for_to:
            if event == Event.to_duration_elapsed:
                # Turn the light back on
                self.engine.set_sw_do('light', 1)
                self.start_timer('iti_duration',
                                 Event.iti_duration_elapsed)
                self.trial_state = TrialState.waiting_for_iti
            elif event in (Event.spout_start, Event.np_start):
                self.timer.cancel()
                self.start_timer('to_duration', Event.to_duration_elapsed)

        elif self.trial_state == TrialState.waiting_for_iti:
            if event == Event.iti_duration_elapsed:
                self.trial_state = TrialState.waiting_for_np_start

    def start_timer(self, variable, event):
        # Even if the duration is 0, we should still create a timer because this
        # allows the `_handle_event` code to finish processing the event. The
        # timer will execute as soon as `_handle_event` finishes processing.
        duration = self.get_value(variable)
        self.timer = threading.Timer(duration, self.handle_event, [event])
        self.timer.start()

    def get_masker(self, masker_offset, masker_duration):
        '''
        Get the next `duration` samples of the masker starting at `offset`. If
        reading past the end of the array, loop around to the beginning.
        '''
        masker_size = self.masker.shape[-1]
        offset = masker_offset % masker_size
        duration = masker_duration
        result = []
        while True:
            if (offset+duration) < masker_size:
                subset = self.masker[offset:offset+duration]
                duration = 0
            else:
                subset = self.masker[offset:]
                offset = 0
                duration = duration-subset.shape[-1]
            result.append(subset)
            if duration == 0:
                break
        return np.concatenate(result, axis=-1)

    def get_target(self):
        return self.target

    def get_ts(self):
        return self.engine.ao_sample_clock()/self.fs


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
    #go_probability = Expression('0.5',
    #        label='Go probability', log=False, context=True)
    repeat_fa = Bool(True, label='Repeat if FA?', log=True, context=True)



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
                'target_filename',
                'target_level',
                'hw_att',
                'test_att',
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

node_name = 'PositiveCMRExperiment'

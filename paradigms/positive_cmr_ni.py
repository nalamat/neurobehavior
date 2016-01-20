import logging
log = logging.getLogger(__name__)

import threading
import warnings

# Available as a built-in module starting with Python 3.4. Backported to python
# 2.7 using the enum34 module. May need to install the enum34 module if not
# already installed. Can remove once we migrate completely to Python 3.4+.
import enum

import numpy as np

from traits.api import Any, Property, Str, Instance, Dict
from daqengine.ni import Engine

from experiments.abstract_experiment_controller import AbstractExperimentController
from experiments.abstract_positive_experiment_v3 import AbstractPositiveExperiment
from experiments.abstract_positive_controller_v3 import AbstractPositiveController
from experiments.abstract_positive_paradigm_v3 import AbstractPositiveParadigm
from experiments.positive_data_v3 import PositiveData
from experiments.positive_cl_data_mixin import PositiveCLDataMixin
from experiments.cl_experiment_mixin import CLExperimentMixin


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


class Controller(AbstractExperimentController):
    '''
    Generic controller that allows for playing a target embedded in a
    continuous background masker.
    '''
    # Track the current state of the experiment. How the controller responds to
    # events will depend on the state.
    trial_state = Instance(TrialState, TrialState.waiting_for_np_start)

    def _get_status(self):
        return self.trial_state.value

    preload_samples = 200000*5
    update_delay = 100000

    _lock = threading.Lock()

    # All experiment controller subclasses are responsible for checking the
    # value of this attribute when making a decision about what the next trial
    # should be.  If True, this means that the user has clicked the "remind"
    # button.
    remind_requested = False
    engine = Instance('daqengine.ni.Engine')

    fs = 200e3

    timer = Instance('threading._Timer')
    trial_type = Str('GO')
    trial_info = Dict()

    def setup_experiment(self, info=None):
        self.trial_state = TrialState.waiting_for_np_start
        self.engine = Engine()
        # Speaker in, mic, nose-poke IR, spout contact IR
        self.engine.configure_hw_ai(self.fs, 'Dev2/ai0:3', (-10, 10))
        # Speaker out
        self.engine.configure_hw_ao(self.fs, 'Dev2/ao0', (-10, 10))
        # Nose poke and spout contact TTL. If we want to monitor additional
        # events occuring in the behavior booth (e.g., room light on/off), we
        # can connect the output controlling the light/pump to an input and
        # monitor state changes on that input.
        self.engine.configure_et('/Dev2/port0/line0:1', 'ao/SampleClock',
                                 names=['spout', 'np'])
        # Control for pump and room light
        #self.engine.configure_sw_do('/Dev2/port1/line0:1',
        #                            names=['pump', 'light'])
        self.engine.register_ao_callback(self.samples_needed)
        self.engine.register_ai_callback(self.samples_acquired)
        self.engine.register_et_callback(self.et_fired)

        self.model.data.microphone.fs = self.fs

        # Load initial set of samples to analog output buffer. This will be the
        # masker alone.
        self._masker_offset = 0
        self.samples_needed(self.preload_samples)

        # TODO: hack
        self.trial_type = 'GO'

    def start_experiment(self, info):
        self.state = 'running'
        log.debug('Preparing next trial')
        self.prepare_next_trial()
        self.engine.start()

    def stop_experiment(self, info):
        self.engine.stop()

    def remind(self, info=None):
        # If trial is already running, the remind will be presented on the next
        # trial.
        self.remind_requested = True

    def start_trial(self):
        # Get the current position in the analog output buffer, and add a cetain
        # update_delay (to give us time to generate and upload the new signal).
        offset = self.get_ts() + self.update_delay
        log.debug('Inserting target at %d', offset)
        # TODO - should be able to calculate a precise duration.
        duration = self.engine.ao_write_space_available(offset)/10
        log.debug('Overwriting %d samples in buffer', duration)

        # Generating combined signal
        signal = self.get_masker(offset, duration)
        target = self.get_target()
        signal[:target.shape[-1]] += target
        self.engine.write_hw_ao(signal, offset)
        self._masker_offset = offset + signal.shape[-1]

        # TODO - the hold duration will include the update delay. Do we need
        # super-precise tracking of hold period or can it vary by a couple 10s
        # to 100s of msec?
        self.trial_state = TrialState.waiting_for_hold_period
        self.start_timer('hold_duration', Event.hold_duration_elapsed)

        # TODO: Verify that these numbers are accurate
        self.trial_info['target_start'] = offset
        self.trial_info['target_end'] = offset+duration

    def stop_trial(self, response):
        if response != 'no response':
            self.trial_info['response_time'] = \
                self.trial_info['response_ts']-self.trial_info['target_start']
        else:
            self.trial_info['response_time'] = np.nan

        self.trial_info['reaction_time'] = \
            self.trial_info['np_end']-self.trial_info['np_start']

        if self.trial_type == 'GO':
            score = 'HIT' if response == 'spout contact' else 'MISS'
        elif self.trial_type == 'NOGO':
            score = 'FA' if response == ' spout contact' else 'CR'

        if score == 'FA':
            # Turn the light off
            self.engine.set_sw_do('light', 0)
            self.start_timer('to_duration', Event.to_duration_elapsed)
            self.trial_state = TrialState.waiting_for_to
        else:
            if score == 'HIT':
                self.engine.fire_sw_do('pump', 0.2)
            self.start_timer('iti_duration', Event.iti_duration_elapsed)
            self.trial_state = TrialState.waiting_for_iti

        self.log_trial(ttype='GO', response=response, **self.trial_info)
        self.trial_info = {}
        self.prepare_next_trial()

    def prepare_next_trial(self):
        log.debug('Preparing next trial')
        self.invalidate_context()
        self.evaluate_pending_expressions()

    ############################################################################
    # Callbacks for NI Engine
    ############################################################################
    def samples_acquired(self, samples):
        # Speaker in, mic, nose-poke IR, spout contact IR
        speaker, mic, np, spout = samples
        self.model.data.microphone.send(speaker)

    def samples_needed(self, samples):
        masker = self.get_masker(self._masker_offset, samples)
        self.engine.write_hw_ao(masker)
        self._masker_offset += samples

    event_map = {
        ('rising', 'np'): Event.np_start,
        ('falling', 'np'): Event.np_end,
        ('rising', 'spout'): Event.spout_start,
        ('falling', 'spout'): Event.spout_end,
    }

    def et_fired(self, edge, line, timestamp):
        event = self.event_map[edge, line]
        self.handle_event(event, timestamp)

    def handle_event(self, event, timestamp=None):
        # Ensure that we don't attempt to process several events at the same
        # time. This essentially queues the events such that the next event
        # doesn't get processed until `_handle_event` finishes processing the
        # current one.
        with self._lock:
            # Only events generated by NI-DAQmx callbacks will have a timestamp.
            # event won't have a timestamp associated with it. Since we want all
            # timing information to be in units of the analog output sample
            # clock, we will capture the value of the sample clock. I don't know
            # what the accuracy of this is, but it's not super-important since
            # these events are not reference points around which we would do a
            # perievent analysis. Important reference points would include
            # nose-poke initiation and withdraw, spout contact, sound onset,
            # lights on, lights off. These reference points will be tracked via
            # NI-DAQmx or can be calculated analytically (i.e., we know exactly
            # when the target onset occurs because we precisely specify the
            # location of the target in the analog output buffer).
            if timestamp is None:
                timestamp = self.get_ts()
            self._handle_event(event, timestamp)

    def _handle_event(self, event, timestamp):
        '''
        Give the current experiment state, process the appropriate response for
        the event that occured. Depending on the experiment state, a particular
        event may not be processed.
        '''
        self.model.data.log_event(timestamp/self.fs, event.value)

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
                if 'np_end' not in self.trial_info:
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
                if 'np_end' not in self.trial_info:
                    self.trial_info['np_end'] = timestamp
            elif event == Event.np_start:
                self.stop_trial(response='nose poke')
                self.trial_info['resp_ts'] = timestamp
            elif event == Event.spout_start:
                self.stop_trial(response='spout contact')
                self.trial_info['resp_ts'] = timestamp
            elif event == Event.response_duration_elapsed:
                self.stop_trial(response='no response')
                self.trial_info['resp_ts'] = timestamp

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
        duration = self.get_value(variable)
        if duration == 0:
            self.handle_event(event)
        else:
            self.timer = threading.Timer(duration, self.handle_event, [event])
            self.timer.start()

    def _get_masker(self, masker_offset, masker_duration):
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

    def get_masker(self, offset, duration):
        t = np.arange(offset, offset+duration, dtype=np.float64)/self.fs
        return np.sin(2*np.pi*t*2)
        #return np.zeros(duration, dtype=np.float32)

    def get_target(self):
        return np.ones(10e3, dtype=np.float32)

    ############################################################################
    # Code to apply parameter changes.
    ############################################################################
    def get_ts(self):
        return self.engine.ao_sample_clock()

    #def set_reward_volume(self, value):
    #    # If the pump volume is set to 0, this actually has the opposite
    #    # consequence of what was intended since a volume of 0 tells the pump
    #    # to deliver water continuously once it recieves a start trigger.
    #    # Instead, to accomodate a reward volume of 0, we turn off the pump
    #    # trigger.
    #    if value == 0:
    #        self.iface_pump.set_trigger(start=None, stop=None)
    #    else:
    #        self.iface_pump.set_trigger(start='rising', stop=None)
    #        self.iface_pump.set_volume(value)
    #        self.iface_pump.set_direction('infuse')


class Paradigm(AbstractPositiveParadigm):
    '''
    Defines the parameters required by the experiment (e.g. duration of various
    events, frequency of the stimulus, which speaker is active, etc.).
    '''
    pass

    # Parameters specific to the actual appetitive paradigm that are not needed
    # by the training program (and therefore not in the "mixin")
    #go_probability = Expression('0.5 if c_nogo < 5 else 1',
    #        label='Go probability', log=False, context=True)
    #repeat_fa = Bool(True, label='Repeat if FA?', log=True, context=True)

    #nogo_filename = File(context=True, log=False, label='NOGO filename')
    #go_filename = File(context=True, log=False, label='GO filename')

    #traits_view = View(
    #        VGroup(
    #            'go_probability',
    #            Include('abstract_positive_paradigm_group'),
    #            Include('pump_paradigm_mixin_syringe_group'),
    #            label='Paradigm',
    #            ),
    #        VGroup(
    #            # Note that because the Paradigm class inherits from
    #            # PositiveCMRParadigmMixin all the parameters defined there are
    #            # available as if they were defined on this class.
    #            Include('speaker_group'),
    #            'hw_att',
    #            'nogo_filename',
    #            'go_filename',
    #            'masker_filename',
    #            'masker_level',
    #            label='Sound',
    #            ),
    #        )


class Data(PositiveData, PositiveCLDataMixin):
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

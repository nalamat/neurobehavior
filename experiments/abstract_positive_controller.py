from enthought.traits.api import Str, Property, Instance
from enthought.traits.ui.api import View, Item, HGroup, spring
from abstract_experiment_controller import AbstractExperimentController
from abstract_experiment_controller import ExperimentToolBar
from cns.pipeline import deinterleave_bits

from cns import get_config
from os.path import join

import numpy as np

import logging
log = logging.getLogger(__name__)

class PositiveExperimentToolBar(ExperimentToolBar):
    
    traits_view = View(
            HGroup(Item('apply',
                        enabled_when="object.handler.pending_changes"),
                   Item('revert',
                        enabled_when="object.handler.pending_changes",),
                   Item('start',
                        enabled_when="object.handler.state=='halted'",),
                   '_',
                   Item('remind',
                        enabled_when="object.handler.state<>'halted'",),
                   Item('stop',
                        enabled_when="object.handler.state in " +\
                                     "['running', 'paused', 'manual']",),
                   spring,
                   springy=True,
                   show_labels=False,
                   ),
            kind='subpanel',
            )

class AbstractPositiveController(AbstractExperimentController):
    
    # Override default implementation of toolbar used by AbstractExperiment
    toolbar = Instance(PositiveExperimentToolBar, (), toolbar=True)

    status = Property(Str, depends_on='state, current_ttype')

    def setup_experiment(self, info):
        circuit = join(get_config('RCX_ROOT'), 'positive-behavior-v2')
        self.iface_behavior = self.process.load_circuit(circuit, 'RZ6')

        # primary speaker
        self.buffer_out1 = self.iface_behavior.get_buffer('out1', 'w')
        # secondary speaker
        self.buffer_out2 = self.iface_behavior.get_buffer('out2', 'w')
        self.buffer_TTL1 = self.iface_behavior.get_buffer('TTL', 'r',
                src_type=np.int8, dest_type=np.int8, block_size=24)
        self.buffer_TTL2 = self.iface_behavior.get_buffer('TTL2', 'r',
                src_type=np.int8, dest_type=np.int8, block_size=24)
        # microphone
        #self.buffer_mic = self.iface_behavior.get_buffer('mic', 'r')
        #self.model.data.microphone.fs = self.buffer_mic.fs

        # Stored in TTL1
        self.model.data.spout_TTL.fs = self.buffer_TTL1.fs
        self.model.data.poke_TTL.fs = self.buffer_TTL1.fs
        self.model.data.signal_TTL.fs = self.buffer_TTL1.fs
        self.model.data.reaction_TTL.fs = self.buffer_TTL1.fs
        self.model.data.response_TTL.fs = self.buffer_TTL1.fs
        self.model.data.reward_TTL.fs = self.buffer_TTL1.fs

        # Stored in TTL2
        self.model.data.TO_TTL.fs = self.buffer_TTL2.fs
        self.model.data.TO_safe_TTL.fs = self.buffer_TTL2.fs
        self.model.data.comm_inhibit_TTL.fs = self.buffer_TTL2.fs

        targets1 = [self.model.data.poke_TTL, self.model.data.spout_TTL,
                    self.model.data.reaction_TTL, self.model.data.signal_TTL,
                    self.model.data.response_TTL, self.model.data.reward_TTL, ]
        targets2 = [self.model.data.TO_safe_TTL, self.model.data.TO_TTL,
                    self.model.data.comm_inhibit_TTL ]

        self.pipeline_TTL1 = deinterleave_bits(targets1)
        self.pipeline_TTL2 = deinterleave_bits(targets2)

        # Configure the pump
        self.iface_pump.set_trigger(start='rising', stop=None)
        self.iface_pump.set_direction('infuse')

    def start_experiment(self, info):
        # What parameters should be available in the context?
        self.initialize_context()
        
        # Grab the current value of the timestamp from the circuit when it is
        # first loaded
        self.current_trial_end_ts = self.get_trial_end_ts()
        self.current_poke_end_ts = self.get_poke_end_ts()

        self.state = 'running'
        self.iface_behavior.trigger('A', 'high')
        
        # Add tasks to the queue
        self.tasks.append((self.monitor_behavior, 1))
        self.tasks.append((self.monitor_pump, 5))
        
        # Prepare the first trial
        self.trigger_next()

    def stop_experiment(self, info):
        self.iface_behavior.trigger('A', 'low')
        self.state = 'halted'

    def _get_status(self):
        if self.state == 'disconnected':
            return 'Error'
        elif self.state == 'halted':
            return 'Halted'
        elif self.current_ttype is not None:
            return self.current_ttype.lower().replace('_', ' ')
        else:
            return ''

    def remind(self, info=None):
        # Pause circuit and see if trial is running. If trial is already
        # running, it's too late and a lock cannot be acquired. If trial is
        # not running, changes can be made. A lock is returned (note this is
        # not thread-safe).
        self.remind_requested = True
        
        # Attempt to apply it immediately. If not, then the remind will be
        # presented on the next trial.
        if self.request_pause():
            self.trigger_next()
            self.request_resume()

    ############################################################################
    # Master controller
    ############################################################################
    def monitor_behavior(self):
        self.pipeline_TTL1.send(self.buffer_TTL1.read())
        self.pipeline_TTL2.send(self.buffer_TTL2.read())
        ts_end = self.get_trial_end_ts()

        if ts_end > self.current_trial_end_ts:
            # Trial is over.  Process new data and set up for next trial.
            self.current_trial_end_ts = ts_end
            ts_start = self.get_trial_start_ts()
            
            while True:
                try:
                    # Since we are compressing 4 samples into a single buffer
                    # slot, we may need to repeat the read twice so we have all
                    # the information we need for analysis of the response.
                    self.pipeline_TTL1.send(self.buffer_TTL1.read_all()) 
                    self.pipeline_TTL2.send(self.buffer_TTL2.read_all())
                    self.log_trial(
                            ts_start=ts_start, 
                            ts_end=ts_end,
                            ttype=self.current_ttype,
                            primary_hw_attenuation=self.current_hw_att1,
                            secondary_hw_attenuation=self.current_hw_att2,
                            )
                    break
                except ValueError, e:
                    log.exception(e)
                    log.debug("Waiting for more data")
                    pass
                
            self.trigger_next()

    def is_go(self):
        return self.current_ttype.startswith('GO')

    ############################################################################
    # Code to apply parameter changes.  This is backend-specific.  If you want
    # to implement a new backend, you would subclass this and override the
    # appropriate set_* methods.
    ############################################################################
    
    def set_poke_duration(self, value):
        # Save requested value for parameter as an attribute because we need
        # this value so we can randomly select a number between the lb and ub
        self.current_poke_duration = value

    def set_intertrial_duration(self, value):
        self.iface_behavior.cset_tag('int_dur_n', value, 's', 'n')

    def set_reaction_window_delay(self, value):
        self.iface_behavior.cset_tag('react_del_n', value, 's', 'n')
        # Check to see if the conversion of s to n resulted in a value of 0.  If
        # so, set the delay to 1 sample (0 means that the reaction window never
        # triggers due to the nature of the RPvds component)
        if self.iface_behavior.get_tag('react_del_n') < 2:
            self.iface_behavior.set_tag('react_del_n', 2)
        self.current_reaction_window_delay = value

        # We need to be sure to update the duration as well if we adjust this
        # value
        self.set_reaction_window_duration(self.current_context['reaction_window_duration'])

    def set_reaction_window_duration(self, value):
        delay = self.get_current_value('reaction_window_delay')
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

    def set_timeout_grace_period(self, value):
        pass

    def set_timeout_trigger(self, value):
        flag = 0 if value == 'FA only' else 1
        self.iface_behavior.set_tag('to_type', flag)

    def set_timeout_duration(self, value):
        self.iface_behavior.cset_tag('to_dur_n', value, 's', 'n')

    def get_trial_running(self):
        return self.iface_behavior.get_tag('trial_running')

    def get_pause_state(self):
        return self.iface_behavior.get_tag('paused?')

    def request_pause(self):
        self.iface_behavior.trigger(2)
        return self.get_pause_state()

    def request_resume(self):
        self.iface_behavior.trigger(3)

    def set_reward_volume(self, value):
        # If the pump volume is set to 0, this actually has the opposite
        # consequence of what was intended since a volume of 0 tells the pump to
        # deliver water continuously once it recieves a start trigger.  Instead,
        # to accomodate a reward volume of 0, we turn off the pump trigger.
        if value == 0:
            self.iface_behavior.set_tag('pump_trig_ms', 0)
        else:
            self.iface_behavior.set_tag('pump_trig_ms', 200)
            self.set_pump_volume(value)

    def set_fa_puff_duration(self, value):
        # The air puff is triggered off of a Schmitt2 component.  If nHi is set
        # to 0, the first TTL to the input of the Schmitt2 will cause the
        # Schmitt2 to go high for infinity.
        self.iface_behavior.cset_tag('puff_dur_n', value, 's', 'n')
        # Check to see if the value of puff_dur_n is 0.  If so, bring it back
        # within the allowed range of values for the Schmitt2 nHi parameter.
        if self.iface_behavior.get_tag('puff_dur_n') == 0:
            self.iface_behavior.set_tag('puff_dur_n', 1)

    def trigger_next(self):
        log.debug('Preparing next trial')
        self.invalidate_context()
        self.current_ttype, self.current_setting = self.next_setting()
        self.evaluate_pending_expressions(self.current_setting)
        
        speaker = self.get_current_value('speaker')

        self.iface_behavior.set_tag('go?', self.is_go())
        log.debug('Trial is %s and speaker is %s', self.current_ttype, speaker)

        # The outputs will automatically handle scaling the waveform given
        # the current hardware attenuation settings.
        if speaker == 'primary':
            att1, waveform1, clip1, floor1 = self.output_primary.realize()
            att2, waveform2 = None, np.zeros(len(waveform1))
            clip2, floor2 = False, False
        elif speaker == 'secondary':
            att2, waveform2, clip2, floor2 = self.output_secondary.realize()
            att1, waveform1 = None, np.zeros(len(waveform2))
            clip1, floor1 = False, False
        elif speaker == 'both':
            att1, waveform1, clip1, floor1 = self.output_primary.realize()
            att2, waveform2, clip2, floor2 = self.output_secondary.realize()

        clip_mesg = 'The {} output exceeds the maximum limits of the system'
        floor_mesg = 'The {} output is below the noise floor of the system'
        message = ''
        if clip1:
            message += clip_mesg.format('primary')
        if clip2:
            message += clip_mesg.format('secondary')
        if floor1:
            message += floor_mesg.format('primary')
        if floor2:
            message += floor_mesg.format('secondary')
        if clip1 or clip2 or floor1 or floor2:
            mesg = '''
            The current experiment settings will produce a distorted signal.
            Please review your settings carefully and correct any discrepancies
            you observe.
            '''
            import textwrap
            mesg = textwrap.dedent(mesg).strip().replace('\n', ' ')
            mesg = message + '\n\n' + mesg
            self.handle_error(mesg)

        # set_attenuations has a built-in safety check to ensure attenuation has
        # not changed.  If it has, indeed, changed and fixed_attenuation is
        # True, then an error will be raised.
        self.set_attenuations(att1, att2)

        self.buffer_out1.set(waveform1)
        self.buffer_out2.set(waveform2)
        self.iface_behavior.trigger(1)

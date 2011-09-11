from enthought.traits.api import Str, Property, Instance, Int
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
                        enabled_when="object.handler.state not in ['halted', 'complete']",),
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
    fs_conversion = Int

    def setup_experiment(self, info):
        circuit = join(get_config('RCX_ROOT'), 'positive-behavior-v2')
        self.iface_behavior = self.process.load_circuit(circuit, 'RZ6')

        # primary speaker
        self.buffer_out1 = self.iface_behavior.get_buffer('out1', 'w')
        # secondary speaker
        self.buffer_out2 = self.iface_behavior.get_buffer('out2', 'w')
        self.buffer_TTL1 = self.iface_behavior.get_buffer('TTL', 'r',
                src_type='int8', dest_type='int8', block_size=24)
        self.buffer_TTL2 = self.iface_behavior.get_buffer('TTL2', 'r',
                src_type='int8', dest_type='int8', block_size=24)
        self.buffer_poke_start = self.iface_behavior.get_buffer('poke_all/',
                'r', src_type='int32', dest_type='int32', block_size=1)
        self.buffer_poke_end = self.iface_behavior.get_buffer('poke_all\\', 'r',
                src_type='int32', dest_type='int32', block_size=1)
        # microphone
        #self.buffer_mic = self.iface_behavior.get_buffer('mic', 'r')
        #self.model.data.microphone.fs = self.buffer_mic.fs

        self.fs_conversion = self.iface_behavior.get_tag('TTL_d')

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

        # Timestamp data
        self.model.data.trial_epoch.fs = self.iface_behavior.fs
        self.model.data.signal_epoch.fs = self.iface_behavior.fs
        self.model.data.poke_epoch.fs = self.iface_behavior.fs
        self.model.data.all_poke_epoch.fs = self.iface_behavior.fs
        self.model.data.response_ts.fs = self.iface_behavior.fs

        targets1 = [self.model.data.poke_TTL, self.model.data.spout_TTL,
                    self.model.data.reaction_TTL, self.model.data.signal_TTL,
                    self.model.data.response_TTL, self.model.data.reward_TTL, ]
        targets2 = [None, self.model.data.TO_TTL,
                    self.model.data.comm_inhibit_TTL ]

        self.pipeline_TTL1 = deinterleave_bits(targets1)
        self.pipeline_TTL2 = deinterleave_bits(targets2)

        # Configure the pump
        self.iface_pump.set_trigger(start='rising', stop=None)
        self.iface_pump.set_direction('infuse')

    def start_experiment(self, info):
        # Grab the current value of the timestamp from the circuit when it is
        # first loaded
        self.current_trial_end_ts = self.get_trial_end_ts()
        self.state = 'running'
        self.process.trigger('A', 'high')
        
        # Add tasks to the queue
        self.tasks.append((self.monitor_behavior, 1))
        self.tasks.append((self.monitor_pump, 5))
        self.trigger_next()

    def stop_experiment(self, info):
        self.process.trigger('A', 'low')

    def remind(self, info=None):
        # Pause circuit and see if trial is running. If trial is already
        # running, it's too late and the remind will be presented on the next
        # trial.
        self.remind_requested = True
        if self.cancel_trigger():
            self.trigger_next()

    ############################################################################
    # Master controller
    ############################################################################
    def monitor_behavior(self):
        self.pipeline_TTL1.send(self.buffer_TTL1.read())
        self.pipeline_TTL2.send(self.buffer_TTL2.read())
        ts_end = self.get_trial_end_ts()
        self.model.data.all_poke_epoch.send(self.get_all_poke_epochs())

        if ts_end > self.current_trial_end_ts:
            # Trial is over.  Process new data and set up for next trial.
            self.current_trial_end_ts = ts_end
            ts_start = self.get_trial_start_ts()

            # Grab the timestamp data for the pertinent events that occured
            # during the trial
            self.model.data.poke_epoch.send([self.get_poke_epoch()])
            self.model.data.signal_epoch.send([self.get_signal_epoch()])
            self.model.data.trial_epoch.send([self.get_trial_epoch()])
            self.model.data.response_ts.send([self.get_response_ts()])

            while True:
                try:
                    # Since we are compressing 4 samples into a single buffer
                    # slot, we may need to repeat the read twice so we have all
                    # the information we need for analysis of the response.
                    self.pipeline_TTL1.send(self.buffer_TTL1.read_all()) 
                    self.pipeline_TTL2.send(self.buffer_TTL2.read_all())

                    # Note that the ts_start and ts_end were originally recorded
                    # at the sampling frequency of the TTL data.  However, we
                    # now have switched to sampling ts_start and ts_end at a
                    # much higher resolution so we can better understand the
                    # timing of the system.  The high resolution ts_start and
                    # ts_end are stored in the trial_epoch array in the data
                    # file while the low resolution (sampled at the TTL rate)
                    # are stored in the trial log.
                    self.log_trial(
                            ts_start=np.floor(ts_start/self.fs_conversion), 
                            ts_end=np.floor(ts_end/self.fs_conversion),
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
        return self.current_setting.ttype.startswith('GO')

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
        duration = self.get_current_value('reaction_window_duration')
        self.set_reaction_window_duration(value)

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

    def get_signal_epoch(self):
        start = self.iface_behavior.get_tag('signal/')
        end = self.iface_behavior.get_tag('signal\\')
        return start, end

    def get_poke_epoch(self):
        start = self.iface_behavior.get_tag('poke/')
        end = self.iface_behavior.get_tag('poke\\')
        return start, end

    def get_trial_epoch(self):
        start = self.iface_behavior.get_tag('trial/')
        end = self.iface_behavior.get_tag('trial\\')
        return start, end

    def get_all_poke_epochs(self):
        # Since there is the distinct possibility of attempting to read the
        # saved poke epochs in the middle of a nose-poke, we need to ensure that
        # we only download the data for which we have complete epochs available.
        ends = self.buffer_poke_end.read().ravel()
        starts = self.buffer_poke_start.read(len(ends)).ravel()
        return zip(starts, ends)

    def get_response_ts(self):
        return self.iface_behavior.get_tag('resp.')

    def get_trial_end_ts(self):
        return self.iface_behavior.get_tag('trial\\')

    def get_trial_start_ts(self):
        return self.iface_behavior.get_tag('trial/')

    def set_timeout_duration(self, value):
        self.iface_behavior.cset_tag('to_dur_n', value, 's', 'n')

    def trial_running(self):
        return self.iface_behavior.get_tag('trial_running')

    def cancel_trigger(self):
        self.iface_behavior.trigger(2)
        return not self.trial_running()

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

    def _context_updated_fired(self):
        if self.cancel_trigger():
            self.trigger_next()

    def trigger_next(self):
        log.debug('Preparing next trial')
        self.invalidate_context()
        self.current_setting = self.next_setting()
        self.evaluate_pending_expressions(self.current_setting)
        
        speaker = self.get_current_value('speaker')
        self.iface_behavior.set_tag('go?', self.is_go())

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
        #if floor1:
        #    message += floor_mesg.format('primary')
        #if floor2:
        #    message += floor_mesg.format('secondary')
        #if clip1 or clip2 or floor1 or floor2:
        if clip1 or clip2:
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

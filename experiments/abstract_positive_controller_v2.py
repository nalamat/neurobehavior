from enthought.traits.api import Instance, Int, Float
from enthought.traits.ui.api import View, Item, HGroup, spring
from abstract_experiment_controller import AbstractExperimentController
from abstract_experiment_controller import ExperimentToolBar
from cns.pipeline import deinterleave_bits
from tdt.device import RZ6

from cns import get_config
from os.path import join

import numpy as np

import logging
log = logging.getLogger(__name__)

class PositiveExperimentToolBar(ExperimentToolBar):

    traits_view = View(
            HGroup(
                Item('apply',
                     enabled_when="object.handler.pending_changes"),
                Item('revert',
                     enabled_when="object.handler.pending_changes",),
                '_',
                Item('start',
                     enabled_when="object.handler.state=='halted'",),
                Item('remind',
                     enabled_when="object.handler.state not in ['halted', 'complete']",),
                Item('stop',
                     enabled_when="object.handler.state in ['running','paused','manual']",),
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

    kw = {'context': True, 'log': True, 'immediate': True}
    hw_att1 = Float(120, label='Out-A attenuation', **kw)
    hw_att2 = Float(120, label='Out-B attenuation', **kw)

    sw_att = Float(120, label='Software attenuation', **kw)
    waveform_rms = Float(-1, label='Waveform RMS', **kw)
    waveform_sf = Float(np.nan, label='Waveform scaling factor', **kw)

    def start_auto(self, info=None):
        self.state = 'auto'
        self.iface_behavior.trigger(3)

    def stop_auto(self, info=None):
        self.state = 'running'
        self.iface_behavior.trigger(2)
        self.iface_behavior.trigger(5)
        
    def set_attenuations(self, att1, att2):
        '''
        Set attenuators for Out-1 and Out-2 on the RZ6.  If either attenuation
        is None, then that attenuation is not changed.  For example, to change
        the attenuation only for Out-2:

        >>> self.set_attenuations(None, 60)

        Note that this only sets the hardware attenuation in valid steps (e.g.
        0, 20, 40 and 60 dB).  The remaining attenuation must be realized via
        scaling of the waveform before it is uploaded to the signal buffer.

        Returns the remaining attenuation that needs to be achieved via scaling
        the waveform.
        '''
        # TDT's built-in attenuators for the RZ6 function in 20 dB steps, so we
        # need to determine the next greater step size for the attenuator.  The
        # maximum hardware attenuation is 60 dB.
        log.debug('Attempting to change attenuation to %r and %r', att1, att2)

        if att1 is None:
            att1 = self.hw_att1
        if att2 is None:
            att2 = self.hw_att2
        hw1, sw1 = RZ6.split_attenuation(att1)
        hw2, sw2 = RZ6.split_attenuation(att2)

        if hw1 != self.hw_att1:
            self.hw_att1 = hw1
            log.debug('Updated primary attenuation to %.2f', hw1)
        if hw2 != self.hw_att2:
            self.hw_att2 = hw2
            log.debug('Updated secondary attenuation to %.2f', hw2)

        # For efficiency reasons, we prefer to do most of the computation for
        # the RZ6 attenuator values in software rather than hardware.
        att_bits = RZ6.atten_to_bits(att1, att2)
        self.iface_behavior.set_tag('att_bits', att_bits)

        # This is the remaining
        return sw1, sw2


    def setup_experiment(self, info):
        circuit = join(get_config('RCX_ROOT'), 'positive-behavior-v2')
        self.iface_behavior = self.process.load_circuit(circuit, 'RZ6')

        self.buffer_out = self.iface_behavior.get_buffer('out', 'w')
        self.buffer_TTL1 = self.iface_behavior.get_buffer('TTL', 'r',
                src_type='int8', dest_type='int8', block_size=24)
        self.buffer_TTL2 = self.iface_behavior.get_buffer('TTL2', 'r',
                src_type='int8', dest_type='int8', block_size=24)
        self.buffer_poke_start = self.iface_behavior.get_buffer('poke_all/',
                'r', src_type='int32', dest_type='int32', block_size=1)
        self.buffer_poke_end = self.iface_behavior.get_buffer('poke_all\\', 'r',
                src_type='int32', dest_type='int32', block_size=1)

        # microphone
        self.buffer_mic = self.iface_behavior.get_buffer('mic', 'r')
        self.model.data.microphone.fs = self.buffer_mic.fs

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

        # Timestamp data
        self.model.data.trial_epoch.fs = self.iface_behavior.fs
        self.model.data.signal_epoch.fs = self.iface_behavior.fs
        self.model.data.poke_epoch.fs = self.iface_behavior.fs
        self.model.data.all_poke_epoch.fs = self.iface_behavior.fs
        self.model.data.response_ts.fs = self.iface_behavior.fs

        targets1 = [self.model.data.poke_TTL, self.model.data.spout_TTL,
                    self.model.data.reaction_TTL, self.model.data.signal_TTL,
                    self.model.data.response_TTL, self.model.data.reward_TTL, ]
        targets2 = [None, self.model.data.TO_TTL]

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
        self.model.data.microphone.send(self.buffer_mic.read())
        self.pipeline_TTL1.send(self.buffer_TTL1.read())
        self.pipeline_TTL2.send(self.buffer_TTL2.read())
        self.model.data.all_poke_epoch.send(self.get_all_poke_epochs())

        # Determine whether the trial is over or not.
        if self.state == 'auto':
            if self.get_trial_time() > self.get_current_value('auto_iti'):
                self.iface_behavior.trigger(5)
            
        if self.get_trial_end_ts() > self.current_trial_end_ts:
            # Trial is over.  Process new data and set up for next trial.
            ts_end = self.get_trial_end_ts()
            self.current_trial_end_ts = ts_end
            ts_start = self.get_trial_start_ts()

            # Grab the timestamp data for the pertinent events that occured
            # during the trial
            self.model.data.signal_epoch.send([self.get_signal_epoch()])
            self.model.data.trial_epoch.send([self.get_trial_epoch()])
            if self.state == 'running':
                self.model.data.response_ts.send([self.get_response_ts()])
                self.model.data.poke_epoch.send([self.get_poke_epoch()])

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
        self.set_reaction_window_duration(duration)

    def set_reaction_window_duration(self, value):
        delay = self.get_current_value('reaction_window_delay')
        self.iface_behavior.cset_tag('react_end_n', delay+value, 's', 'n')

    def set_response_window_duration(self, value):
        self.iface_behavior.cset_tag('resp_dur_n', value, 's', 'n')

    def set_signal_offset_delay(self, value):
        self.iface_behavior.cset_tag('sig_offset_del_n', value, 's', 'n')

    def get_ts(self, req_unit=None):
        return self.iface_behavior.get_tag('zTime')

    def get_trial_time(self):
        return self.iface_behavior.cget_tag('iTrialTime', 'n', 's')

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
        return self.iface_behavior.get_tag('resp|')

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

    def set_mic_fhp(self, value):
        self.iface_behavior.set_tag('FiltHP', value)

    def set_mic_flp(self, value):
        self.iface_behavior.set_tag('FiltLP', value)

    def context_updated(self):
        if self.cancel_trigger():
            self.trigger_next()

    def trigger_next(self):
        log.debug('Preparing next trial')
        self.invalidate_context()
        self.current_setting = self.next_setting()
        self.evaluate_pending_expressions(self.current_setting)
        
        speaker = self.get_current_value('speaker')
        self.iface_behavior.set_tag('go?', self.is_go())

        # The RPvds circuit has a flag indicating which speaker to send the
        # waveform to.  0=primary, 1=secondary (i.e. Out-1 and Out-2,
        # respectively).
        if speaker == 'primary':
            calibration = self.cal_primary
            hw_atten = self.hw_att1
            self.iface_behavior.set_tag('speaker', 0)
        elif speaker == 'secondary':
            calibration = self.cal_secondary
            hw_atten = self.hw_att2
            self.iface_behavior.set_tag('speaker', 1)

        waveform, attenuation = self.compute_waveform(calibration, hw_atten)
        if speaker == 'primary':
            sw_att = self.set_attenuations(attenuation, None)[0]
        elif speaker == 'secondary':
            sw_att = self.set_attenuations(None, attenuation)[1]

        # Scale by this much to achieve remaining software attenuation
        sf = 10**(-sw_att/20.0)

        # Save some information about these that will be stored in the tria log
        self.sw_att = sw_att
        self.waveform_sf = sf
        self.waveform_rms = sf*(np.mean(waveform**2)**0.5)

        log.debug('Remaining software attenuation of %f dB required', sw_att)
        log.debug('Scaling waveform by %f to compensate', sf)
        log.debug('Uploading %d samples', len(waveform))

        self.buffer_out.set(sf*waveform)
        self.iface_behavior.trigger(1)

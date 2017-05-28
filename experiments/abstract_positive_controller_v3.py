'''
..module:: experiments.abstract_positive_experiment_v3
    :platform: Windows
    :synopsis: Base class for appetitive paradigms

.. moduleauthor:: Brad Buran <bburan@alum.mit.edu>
.. moduleauthor:: Gardiner von Trapp <gvontrapp@cns.nyu.edu>

A version of the appetitive paradigm that does not include a reaction window.
'''

from traits.api import Instance, Int, Float, Any, Bool
from traitsui.api import View, Item, HGroup, spring
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

    kw = {'context': True, 'log': True, 'immediate': True}
    hw_att1 = Float(120, label='Out-A attenuation', **kw)
    hw_att2 = Float(120, label='Out-B attenuation', **kw)

    sw_att = Float(120, label='Software attenuation', **kw)
    waveform_rms = Float(-1, label='Waveform RMS', **kw)
    waveform_sf = Float(np.nan, label='Waveform scaling factor', **kw)
    waveform_min = Float(np.nan, label='Waveform max', **kw)
    waveform_max = Float(np.nan, label='Waveform max', **kw)

    pipeline_TTL1   = Any
    pipeline_TTL2   = Any
    
    # All experiment controller subclasses are responsible for checking the
    # value of this attribute when making a decision about what the next trial
    # should be.  If True, this means that the user has clicked the "remind"
    # button.
    remind_requested = Bool(False)

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
        # This function gets called every ~100 msec (this time interval is not
        # guaranteed).  Essentially this is a loop that queries the RPvds
        # circuit, downloads all new data (and saves it to the PositiveData
        # object which is a proxy for the HDF5 file -- the PositiveData object
        # is required as a proxy rather than dumping the data directly to the
        # HDF5 file because the PositiveData object also updates the GUI plots
        # as well).  This function is also responsible for determining when a
        # trial is over (when the value of trial_end_ts in the RPvds circuit
        # changes this indicates that a trial is over).  When a trial is over,
        # monitor_behavior calls the trigger_next() method to setup the next
        # trial.
        self.model.data.microphone.send(self.buffer_mic.read())
        self.pipeline_TTL1.send(self.buffer_TTL1.read())
        self.pipeline_TTL2.send(self.buffer_TTL2.read())
        ts_end = self.get_trial_end_ts()
        self.model.data.all_poke_epoch.send(self.get_all_poke_epochs())

        if ts_end > self.current_trial_end_ts:
            # Trial is over because the end timestamp in the circuit has
            # changed.  Download all necessary data from the RPvds circuit and
            # set up for the new trial.
            self.current_trial_end_ts = ts_end
            ts_start = self.get_trial_start_ts()

            # Grab the timestamp data for the pertinent events that occured
            # during the trial
            self.model.data.poke_epoch.send([self.get_poke_epoch()])
            self.model.data.signal_epoch.send([self.get_signal_epoch()])
            self.model.data.trial_epoch.send([self.get_trial_epoch()])
            self.model.data.response_ts.send([self.get_response_ts()])

            # Find out what the response was
            poke = self.iface_behavior.get_tag('resp_poke?')
            spout = self.iface_behavior.get_tag('resp_spout?')
            to = self.iface_behavior.get_tag('fa?')
            if to:
                response = 'spout'
            elif poke and not spout:
                response = 'poke'
            elif spout and not poke:
                response = 'spout'
            elif not (spout or poke):
                response = 'no response'
            else:
                raise ValueError, "Unknown response type!"

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
                            response=response,
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
    
    def set_intertrial_duration(self, value):
        self.iface_behavior.cset_tag('int_dur_n', value, 's', 'n')

    def set_response_window_delay(self, value):
        self.iface_behavior.cset_tag('resp_del_n', value, 's', 'n')
        # Check to see if the conversion of s to n resulted in a value of 0.  If
        # so, set the delay to 1 sample (0 means that the respion window never
        # triggers due to the nature of the RPvds component)
        if self.iface_behavior.get_tag('resp_del_n') < 2:
            self.iface_behavior.set_tag('resp_del_n', 2)

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
        '''
        Check to see if it's possible to cancel the next trial.  If so,
        recompute the waveform and trial settings based on the new values
        provided by the user.  If not, just wait until after the trial is over.
        '''
        if self.cancel_trigger():
            self.trigger_next()

    def compute_waveform(self, calibration, hw_attenuation):
        '''
        Must be implemented by the specific paradigms.

        Should return the waveform (scaled as needed) and the relevant
        attenuation value.
        '''
        raise NotImplementedError

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
        log.debug('You are now inside %s.trigger_next()', __name__)
        log.debug('compute_waveform() has requested an attenuation of %f',
                  attenuation)

        log.debug('Now configuring the hardware attenuation')
        log.debug('This step computes the best hardware attenuation')
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
        waveform = waveform * sf

        self.waveform_min = waveform.min()
        self.waveform_max = waveform.max()

        log.debug('Remaining software attenuation of %f dB required', sw_att)
        log.debug('Scaling waveform by %f to compensate', sf)
        log.debug('Waveform spans %f to %f Volts (peak to peak)',
                  self.waveform_min, self.waveform_max)
        log.debug('Uploading %d samples', len(waveform))

        self.buffer_out.set(waveform)
        self.iface_behavior.trigger(1)

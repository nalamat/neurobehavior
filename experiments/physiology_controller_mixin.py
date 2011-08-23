import numpy as np
from enthought.traits.api import (HasTraits, Instance, Any, List,
        on_trait_change, Undefined)
from enthought.traits.ui.api import HGroup, View, Item
from tdt import DSPProcess
from cns import get_config
from os.path import join
from cns.pipeline import deinterleave_bits

CHANNELS = get_config('PHYSIOLOGY_CHANNELS')

class PhysiologyControllerMixin(HasTraits):

    # By convention, all mixin classes should prepend attribute names with the
    # mixin name (e.g. physiology). This prevents potential namespace
    # collisions if we are using more than one mixin.
    iface_physiology        = Any
    buffer_physiology_raw   = Any
    buffer_physiology_proc  = Any
    buffer_physiology_ts    = Any
    buffer_physiology_ttl   = Any
    physiology_ttl_pipeline = Any
    buffer_spikes           = List(Any)

    def close(self, info, is_ok):
        '''
        Prevent user from closing window while an experiment is running since
        data is not saved to file until the stop button is pressed.
        '''

        # We can abort a close event by returning False.  If an experiment
        # is currently running, confirm that the user really did want to close
        # the window.  If no experiment is running, then it's OK since the user
        # can always restart the experiment.
        if self.state not in ('disconnected', 'halted', 'complete'):
            mesg = 'Experiment is still running.  Are you sure you want to exit?'

            # The function confirm returns an integer that represents the
            # response that the user requested.  YES is a constant (also
            # imported from the same module as confirm) corresponding to the
            # return value of confirm when the user presses the "yes" button on
            # the dialog.  If any other button (e.g. "no", "abort", etc.) is
            # pressed, the return value will be something other than YES and we
            # will assume that the user has requested not to quit the
            # experiment.
            if confirm(info.ui.control, mesg) == YES:
                self.stop(info)
                return True
            else:
                return False
        else:
            return True

    @on_trait_change('model.physiology_settings.channel_settings:spike_threshold')
    def _update_threshold(self, channel, name, old, new):
        if self.iface_physiology is not None:
            tag_name = 'a_spike{}'.format(channel.number)
            self.iface_physiology.set_tag(tag_name, new)
            
    @on_trait_change('model.physiology_settings.channel_settings:spike_windows')
    def _update_windows(self, channel, name, old, new):
        if self.iface_physiology is not None:
            tag_name = 'c_spike{}'.format(channel.number)
            self.iface_physiology.set_sort_windows(tag_name, new)
            #history = len(self.model.data.physiology_spikes[channel].buffer)
            #self.model.physiology_sort_plot.last_reset = history
        
    def setup_physiology(self):
        # Load the circuit
        circuit = join(get_config('RCX_ROOT'), 'physiology')
        self.iface_physiology = self.process.load_circuit(circuit, 'RZ5')

        # Initialize the buffers that will be spooling the data
        self.buffer_physiology_raw = self.iface_physiology.get_buffer('craw',
                'r', src_type='int16', dest_type='float32', channels=CHANNELS)
        self.buffer_physiology_filt = self.iface_physiology.get_buffer('cfilt',
                'r', src_type='int16', dest_type='float32', channels=CHANNELS)
        self.buffer_physiology_ts = self.iface_physiology.get_buffer('trig/',
                'r', src_type='int32', dest_type='int32', block_size=1)
        self.buffer_physiology_ttl = self.iface_physiology.get_buffer('TTL',
                'r', src_type='int8', dest_type='int8', block_size=1)

        for i in range(CHANNELS):
            name = 'spike{}'.format(i+1)
            buffer = self.iface_physiology.get_buffer(name, 'r', block_size=40)
            self.buffer_spikes.append(buffer)
            self.model.data.physiology_spikes[i].fs = buffer.fs

        # Ensure that the data store has the correct sampling frequency
        self.model.data.physiology_raw.fs = self.buffer_physiology_raw.fs
        self.model.data.physiology_processed.fs = self.buffer_physiology_filt.fs
        self.model.data.physiology_ram.fs = self.buffer_physiology_raw.fs
        self.model.data.physiology_ts.fs = self.buffer_physiology_ts.fs
        self.model.data.physiology_sweep.fs = self.buffer_physiology_ttl.fs

        targets = [self.model.data.physiology_sweep]
        self.physiology_ttl_pipeline = deinterleave_bits(targets)

    def monitor_physiology(self):
        # Acquire raw physiology data
        waveform = self.buffer_physiology_raw.read()
        self.model.data.physiology_raw.send(waveform)

        # Acquire filtered physiology data
        waveform = self.buffer_physiology_filt.read()
        self.model.data.physiology_processed.send(waveform)

        # Acquire sweep data
        ttl = self.buffer_physiology_ttl.read()
        self.physiology_ttl_pipeline.send(ttl)

        # Get the timestamps
        ts = self.buffer_physiology_ts.read()
        self.model.data.physiology_ts.send(ts)

        # Get the spikes.  Each channel has a separate buffer for the spikes
        # detected online.
        for i in range(CHANNELS):
            data = self.buffer_spikes[i].read().reshape((-1, 40))

            # First sample of each snippet is the timestamp (as a 32 bit
            # integer) and last sample is the classifier (also as a 32 bit
            # integer)
            snip = data[:,1:-1]
            ts = data[:,0].view('int32')
            cl = data[:,-1].view('int32')
            self.model.data.physiology_spikes[i].send(snip, ts, cl)
            
    def set_spike_thresholds(self, value):
        for ch, threshold in enumerate(value):
            name = 'a_spike{}'.format(ch+1)
            self.iface_physiology.set_tag(name, threshold)
            
    def set_monitor_fc_highpass(self, value):
        self.iface_physiology.set_tag('FiltHP', value)

    def set_monitor_fc_lowpass(self, value):
        self.iface_physiology.set_tag('FiltLP', value)

    def set_monitor_ch_1(self, value):
        self.iface_physiology.set_tag('ch1_out', value)

    def set_monitor_ch_2(self, value):
        self.iface_physiology.set_tag('ch2_out', value)

    def set_monitor_ch_3(self, value):
        self.iface_physiology.set_tag('ch3_out', value)

    def set_monitor_ch_4(self, value):
        self.iface_physiology.set_tag('ch4_out', value)

    def set_monitor_gain_1(self, value):
        self.iface_physiology.set_tag('ch1_out_sf', value*1e3)

    def set_monitor_gain_2(self, value):
        self.iface_physiology.set_tag('ch2_out_sf', value*1e3)

    def set_monitor_gain_3(self, value):
        self.iface_physiology.set_tag('ch3_out_sf', value*1e3)

    def set_monitor_gain_4(self, value):
        self.iface_physiology.set_tag('ch4_out_sf', value*1e3)

    def set_visible_channels(self, value):
        self.model.physiology_plot.channel_visible = value

    def set_diff_matrix(self, value):
        self.iface_physiology.set_coefficients('diff_map', value.ravel())

    def set_commutator_inhibit(self, value):
        self.iface_behavior.set_tag('comm_inhibit', value)

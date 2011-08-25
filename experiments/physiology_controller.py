import numpy as np
from enthought.traits.api import (HasTraits, Instance, Any, List,
        on_trait_change, Undefined, Enum)

from enthought.traits.ui.api import Controller
from enthought.pyface.api import error
from enthought.pyface.timer.api import Timer

from tdt import DSPProject
from cns import get_config
from os.path import join
from cns.pipeline import deinterleave_bits

CHANNELS = get_config('PHYSIOLOGY_CHANNELS')
PHYSIOLOGY_WILDCARD = get_config('PHYSIOLOGY_WILDCARD')
SPIKE_SNIPPET_SIZE = 20
PHYSIOLOGY_ROOT = get_config('PHYSIOLOGY_ROOT')

from .utils import get_save_file, load_instance, dump_instance

class PhysiologyController(Controller):

    # By convention, all mixin classes should prepend attribute names with the
    # mixin name (e.g. physiology). This prevents potential namespace
    # collisions if we are using more than one mixin.
    buffer_                 = Any
    iface_physiology        = Any
    buffer_physiology_raw   = Any
    buffer_physiology_proc  = Any
    buffer_physiology_ts    = Any
    buffer_physiology_ttl   = Any
    physiology_ttl_pipeline = Any
    buffer_spikes           = List(Any)
    state                   = Enum('master', 'client')
    process                 = Instance(DSPProject, ())
    timer                   = Instance(Timer)
    parent                  = Any

    def init(self, info):
        self.setup_physiology()
        self.model = info.object
        if self.state == 'master':
            self.process.start()
            self.iface_physiology.trigger('A', 'high')
            self.start()

    def close(self, info, is_ok, from_parent=False):
        return True
        if self.state == 'client':
            return from_parent
        else:
            # The function confirm returns an integer that represents the
            # response that the user requested.  YES is a constant (also
            # imported from the same module as confirm) corresponding to the
            # return value of confirm when the user presses the "yes" button on
            # the dialog.  If any other button (e.g. "no", "abort", etc.) is
            # pressed, the return value will be something other than YES and we
            # will assume that the user has requested not to quit the
            # experiment.
            if confirm(info.ui.control, 'OK to stop?') == YES:
                self.stop(info)
                return True
            else:
                return False

    def setup_physiology(self):
        # Load the circuit
        circuit = join(get_config('RCX_ROOT'), 'physiology')
        self.iface_physiology = self.process.load_circuit(circuit, 'RZ5')

        # Initialize the buffers that will be spooling the data
        self.buffer_physiology_raw = self.iface_physiology.get_buffer('craw',
                'r', src_type='int16', dest_type='float32', channels=CHANNELS,
                block_size=1048)
        self.buffer_physiology_filt = self.iface_physiology.get_buffer('cfilt',
                'r', src_type='int16', dest_type='float32', channels=CHANNELS,
                block_size=1048)
        self.buffer_physiology_ts = self.iface_physiology.get_buffer('trig/',
                'r', src_type='int32', dest_type='int32', block_size=1)
        self.buffer_physiology_ttl = self.iface_physiology.get_buffer('TTL',
                'r', src_type='int8', dest_type='int8', block_size=1)


        for i in range(CHANNELS):
            name = 'spike{}'.format(i+1)
            buffer = self.iface_physiology.get_buffer(name, 'r',
                    block_size=SPIKE_SNIPPET_SIZE)
            self.buffer_spikes.append(buffer)
            spikes = self.model.data.physiology_spikes[i] 
            spikes.snippet_size = SPIKE_SNIPPET_SIZE-2
            spikes.fs = buffer.fs

    @on_trait_change('model.data')
    def update_data(self):
        # Ensure that the data store has the correct sampling frequency
        for i in range(CHANNELS):
            data_spikes = self.model.data.physiology_spikes
            for src, dest in zip(self.buffer_spikes, data_spikes):
                dest.fs = src.fs
        self.model.data.physiology_raw.fs = self.buffer_physiology_raw.fs
        self.model.data.physiology_processed.fs = self.buffer_physiology_filt.fs
        self.model.data.physiology_ram.fs = self.buffer_physiology_raw.fs
        self.model.data.physiology_ts.fs = self.buffer_physiology_ts.fs
        self.model.data.physiology_sweep.fs = self.buffer_physiology_ttl.fs

        # Setup the pipeline
        targets = [self.model.data.physiology_sweep]
        self.physiology_ttl_pipeline = deinterleave_bits(targets)

    def start(self):
        self.timer = Timer(100, self.monitor_physiology)

    def stop(self):
        self.timer.stop()
        self.process.stop()

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
            data = self.buffer_spikes[i].read().reshape((-1,
                SPIKE_SNIPPET_SIZE))

            # First sample of each snippet is the timestamp (as a 32 bit
            # integer) and last sample is the classifier (also as a 32 bit
            # integer)
            snip = data[:,1:-1]
            ts = data[:,0].view('int32')
            cl = data[:,-1].view('int32')
            self.model.data.physiology_spikes[i].send(snip, ts, cl)

    @on_trait_change('model.settings.spike_thresholds')
    def set_spike_thresholds(self, value):
        for ch, threshold in enumerate(value):
            name = 'a_spike{}'.format(ch+1)
            self.iface_physiology.set_tag(name, threshold)
            
    def set_spike_signs(self, value):
        for ch, sign in enumerate(value):
            name = 's_spike{}'.format(ch+1)
            self.iface_physiology.set_tag(name, sign)
            
    @on_trait_change('model.settings.monitor_fc_highpass')
    def set_monitor_fc_highpass(self, value):
        self.iface_physiology.set_tag('FiltHP', value)

    @on_trait_change('model.settings.monitor_fc_lowpass')
    def set_monitor_fc_lowpass(self, value):
        self.iface_physiology.set_tag('FiltLP', value)

    @on_trait_change('model.settings.monitor_ch_1')
    def set_monitor_ch_1(self, value):
        self.iface_physiology.set_tag('ch1_out', value)

    @on_trait_change('model.settings.monitor_ch_2')
    def set_monitor_ch_2(self, value):
        self.iface_physiology.set_tag('ch2_out', value)

    @on_trait_change('model.settings.monitor_ch_3')
    def set_monitor_ch_3(self, value):
        self.iface_physiology.set_tag('ch3_out', value)

    @on_trait_change('model.settings.monitor_ch_4')
    def set_monitor_ch_4(self, value):
        self.iface_physiology.set_tag('ch4_out', value)

    @on_trait_change('model.settings.monitor_gain_1')
    def set_monitor_gain_1(self, value):
        self.iface_physiology.set_tag('ch1_out_sf', value*1e3)

    @on_trait_change('model.settings.monitor_gain_2')
    def set_monitor_gain_2(self, value):
        self.iface_physiology.set_tag('ch2_out_sf', value*1e3)

    @on_trait_change('model.settings.monitor_gain_3')
    def set_monitor_gain_3(self, value):
        self.iface_physiology.set_tag('ch3_out_sf', value*1e3)

    @on_trait_change('model.settings.monitor_gain_4')
    def set_monitor_gain_4(self, value):
        self.iface_physiology.set_tag('ch4_out_sf', value*1e3)

    @on_trait_change('model.settings.visible_channels')
    def set_visible_channels(self, value):
        self.model.physiology_plot.channel_visible = value

    @on_trait_change('model.settings.diff_matrix')
    def set_diff_matrix(self, value):
        self.iface_physiology.set_coefficients('diff_map', value.ravel())

    @on_trait_change('model:settings:channel_settings:spike_threshold')
    def _update_threshold(self, channel, name, old, new):
        if self.iface_physiology is not None:
            tag_name = 'a_spike{}'.format(channel.number)
            self.iface_physiology.set_tag(tag_name, new)
            
    @on_trait_change('model:settings:channel_settings:spike_windows')
    def _update_windows(self, channel, name, old, new):
        print channel
        if self.iface_physiology is not None:
            tag_name = 'c_spike{}'.format(channel.number)
            self.iface_physiology.set_sort_windows(tag_name, new)
            #history = len(self.model.data.physiology_spikes[channel].buffer)
            #self.model.physiology_sort_plot.last_reset = history
        
    def load_settings(self, info):
        instance = load_instance(PHYSIOLOGY_ROOT, PHYSIOLOGY_WILDCARD)
        if instance is not None:
            self.model.settings = instance

    def saveas_settings(self, info):
        dump_instance(self.model.settings, PHYSIOLOGY_ROOT, PHYSIOLOGY_WILDCARD)

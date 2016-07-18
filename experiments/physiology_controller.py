from traits.api import (Instance, Any, List, on_trait_change, Enum,
                                  Dict)

from traitsui.api import Controller
from pyface.timer.api import Timer

from cns import get_config
from os.path import join
from cns.pipeline import deinterleave_bits

CHANNELS = get_config('PHYSIOLOGY_CHANNELS')
PHYSIOLOGY_WILDCARD = get_config('PHYSIOLOGY_WILDCARD')
SPIKE_SNIPPET_SIZE = get_config('PHYSIOLOGY_SPIKE_SNIPPET_SIZE')

from .utils import load_instance, dump_instance

class PhysiologyController(Controller):

    buffer_                 = Any
    iface_physiology        = Any
    buffer_raw              = Any
    buffer_proc             = Any
    buffer_ts               = Any
    buffer_ttl              = Any
    physiology_ttl_pipeline = Any
    buffer_spikes           = List(Any)
    state                   = Enum('master', 'client')
    process                 = Instance('tdt.DSPProject')
    timer                   = Instance(Timer)
    parent                  = Any

    shell_variables         = Dict

    # These define what variables will be available in the Python shell.  Right
    # now we can't add various stuff such as the data and interface classes
    # because they have not been created yet.  I'm not sure how we can update
    # the Python shell with new instances once the experiment has started
    # running.
    def _shell_variables_default(self):
        return dict(controller=self, c=self)

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
        self.buffer_raw = self.iface_physiology.get_buffer('craw',
                'r', src_type='float32', dest_type='float32', channels=CHANNELS,
                block_size=1048)
        self.buffer_filt = self.iface_physiology.get_buffer('cfilt',
                'r', src_type='int16', dest_type='float32', channels=CHANNELS,
                block_size=1048)
        self.buffer_ts = self.iface_physiology.get_buffer('trig/',
                'r', src_type='int32', dest_type='int32', block_size=1)
        self.buffer_ts_start = self.iface_physiology.get_buffer('trig/',
                'r', src_type='int32', dest_type='int32', block_size=1)
        self.buffer_ts_end = self.iface_physiology.get_buffer('trig\\',
                'r', src_type='int32', dest_type='int32', block_size=1)
        self.buffer_ttl = self.iface_physiology.get_buffer('TTL',
                'r', src_type='int8', dest_type='int8', block_size=1)

        for i in range(CHANNELS):
            name = 'spike{}'.format(i+1)
            buffer = self.iface_physiology.get_buffer(name, 'r',
                    block_size=SPIKE_SNIPPET_SIZE+2)
            self.buffer_spikes.append(buffer)

    @on_trait_change('model.data')
    def update_data(self):
        # Ensure that the data store has the correct sampling frequency
        for i in range(CHANNELS):
            data_spikes = self.model.data.spikes
            for src, dest in zip(self.buffer_spikes, data_spikes):
                dest.fs = src.fs
                dest.snippet_size = SPIKE_SNIPPET_SIZE
        self.model.data.raw.fs = self.buffer_raw.fs
        self.model.data.processed.fs = self.buffer_filt.fs
        self.model.data.ts.fs = self.iface_physiology.fs
        self.model.data.epoch.fs = self.iface_physiology.fs
        self.model.data.sweep.fs = self.buffer_ttl.fs

        # Setup the pipeline
        targets = [self.model.data.sweep]
        self.physiology_ttl_pipeline = deinterleave_bits(targets)

    def start(self):
        self.timer = Timer(100, self.monitor_physiology)

    def stop(self):
        self.timer.stop()
        self.process.stop()

    def monitor_physiology(self):
        # Acquire raw physiology data
        waveform = self.buffer_raw.read()
        self.model.data.raw.send(waveform)

        # Acquire filtered physiology data
        waveform = self.buffer_filt.read()
        self.model.data.processed.send(waveform)

        # Acquire sweep data
        ttl = self.buffer_ttl.read()
        self.physiology_ttl_pipeline.send(ttl)

        # Get the timestamps
        ts = self.buffer_ts.read().ravel()
        self.model.data.ts.send(ts)

        ends = self.buffer_ts_end.read().ravel()
        starts = self.buffer_ts_start.read(len(ends)).ravel()
        self.model.data.epoch.send(zip(starts, ends))

        # Get the spikes.  Each channel has a separate buffer for the spikes
        # detected online.  Need to add 2 to the snippet size to compensate for
        # the extra samples provided with the snippet (the timestamp and the
        # classifier).
        snippet_shape = (-1, SPIKE_SNIPPET_SIZE+2)
        for i in range(CHANNELS):
            data = self.buffer_spikes[i].read().reshape(snippet_shape)

            # First sample of each snippet is the timestamp (as a 32 bit
            # integer) and last sample is the classifier (also as a 32 bit
            # integer).  The bits in between should be interpreted as 32-bit
            # floating point values.
            snip = data[:,1:-1]
            ts = data[:,0].view('int32')
            cl = data[:,-1].view('int32')
            self.model.data.spikes[i].send(snip, ts, cl)

    @on_trait_change('model.settings.spike_signs')
    def set_spike_signs(self, value):
        for ch, sign in enumerate(value):
            name = 's_spike{}'.format(ch+1)
            self.iface_physiology.set_tag(name, sign)

    @on_trait_change('model.settings.spike_thresholds')
    def set_spike_thresholds(self, value):
        for ch, threshold in enumerate(value):
            name = 'a_spike{}'.format(ch+1)
            self.iface_physiology.set_tag(name, threshold)

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

    @on_trait_change('model.settings.monitor_gain_1')
    def set_monitor_gain_1(self, value):
        self.iface_physiology.set_tag('ch1_out_sf', value*1e3)

    @on_trait_change('model.settings.monitor_gain_2')
    def set_monitor_gain_2(self, value):
        self.iface_physiology.set_tag('ch2_out_sf', value*1e3)

    @on_trait_change('model.settings.monitor_gain_3')
    def set_monitor_gain_3(self, value):
        self.iface_physiology.set_tag('ch3_out_sf', value*1e3)

    @on_trait_change('model.settings.diff_matrix')
    def set_diff_matrix(self, value):
        self.iface_physiology.set_coefficients('diff_map', value.ravel())

    def load_settings(self, info):
        instance = load_instance(PHYSIOLOGY_ROOT, PHYSIOLOGY_WILDCARD)
        if instance is not None:
            self.model.settings.copy_traits(instance)

    def saveas_settings(self, info):
        dump_instance(self.model.settings, PHYSIOLOGY_ROOT, PHYSIOLOGY_WILDCARD)

    @on_trait_change('model.channel_mode')
    def _channel_mode_changed(self, new):
        if new == 'TDT':
            offset = 0
        elif new =='TBSI':
            offset = 1
        else:
            offset = 2
        self.iface_physiology.set_tag('ch_offset', offset*16+1)

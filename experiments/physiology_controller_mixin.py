from enthought.traits.api import HasTraits, Instance, Any
from tdt import DSPProcess
from cns import RCX_ROOT
from os.path import join

class PhysiologyControllerMixin(HasTraits):

    # By convention, all mixin classes should prepend attribute names with the
    # mixin name (e.g. physiology).  This prevents potential namespace
    # collisions.
    iface_physiology        = Any
    buffer_physiology_raw   = Any
    buffer_physiology_ts    = Any

    def setup_physiology(self):
        # Load the circuit
        circuit = join(RCX_ROOT, 'physiology')
        self.iface_physiology = self.process.load_circuit(circuit, 'RZ5')

        # Initialize the buffers that will be spooling the data
        self.buffer_physiology_raw = self.iface_physiology.get_buffer('craw',
                'r', src_type='int16', dest_type='float32', channels=16) 
        self.buffer_physiology_ts = self.iface_physiology.get_buffer('trig/',
                'r', src_type='int32', dest_type='int32', block_size=1)

        # Ensure that the data store has the correct sampling frequency
        self.model.data.physiology_raw.fs = self.buffer_physiology_raw.fs
        self.model.data.physiology_ram.fs = self.buffer_physiology_raw.fs
        self.model.data.physiology_ts.fs = self.buffer_physiology_ts.fs
        
        # Start the circuit
        #self.iface_physiology.start()

    def monitor_physiology(self):
        # Acquire spooled physiology data and send it to the HDF5 store plus the
        # memory "shadow" copy
        waveform = self.buffer_physiology_raw.read()
        self.model.data.physiology_raw.send(waveform)
        self.model.data.physiology_ram.send(waveform)
        # Get the timestamps
        ts = self.buffer_physiology_ts.read()
        self.model.data.physiology_ts.send(ts)

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
        self.model.physiology_plot.visible = value

    def set_diff_matrix(self, value):
        print value

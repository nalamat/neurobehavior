from enthought.traits.api import Property, Str

#from tdt import DSPCircuit
from cns.pipeline import deinterleave_bits
from cns.data.h5_utils import append_date_node, append_node
from cns.data.persistence import add_or_update_object

from abstract_experiment_controller import AbstractExperimentController
from pump_controller_mixin import PumpControllerMixin
from positive_stage1_data import PositiveStage1Data

from os.path import join
from cns import RCX_ROOT

class PositiveStage1Controller(AbstractExperimentController,
        PumpControllerMixin):

    status = Property(Str, depends_on='state')

    def setup_experiment(self, info):
        circuit = join(RCX_ROOT, 'positive-behavior-stage1')
        self.iface_behavior = self.process.load_circuit(circuit, 'RZ6')
        self.buffer_signal = self.iface_behavior.get_buffer('signal', 'w')
        self.buffer_TTL = self.iface_behavior.get_buffer('TTL', 'r',
                block_size=24, src_type='int8', dest_type='int8')

    def start_experiment(self, info):
        self.init_context()
        self.update_context()
        self.iface_pump.set_trigger(start='rising', stop='falling')
        self.iface_pump.set_direction('infuse')
        self.iface_pump.set_volume(0)

        # Set up data collection
        self.init_signal()

        self.model.data.spout_TTL.fs = self.buffer_TTL.fs
        self.model.data.override_TTL.fs = self.buffer_TTL.fs
        self.model.data.pump_TTL.fs = self.buffer_TTL.fs
        self.model.data.signal_TTL.fs = self.buffer_TTL.fs
        self.model.data.free_run_TTL.fs = self.buffer_TTL.fs

        targets = [self.model.data.spout_TTL,
                   self.model.data.override_TTL,
                   self.model.data.pump_TTL, 
                   self.model.data.signal_TTL,
                   self.model.data.free_run_TTL ]

        self.pipeline_TTL = deinterleave_bits(targets)

        self.iface_behavior.start()
        self.pause(info)

        self.tasks.append((self.monitor_pump, 5))
        self.tasks.append((self.monitor_behavior, 1))

    def resume(self, info=None):
        self.iface_behavior.set_tag('free_run?', 1)
        self.state = 'running'

    def pause(self, info=None):
        self.iface_behavior.set_tag('free_run?', 0)
        self.state = 'paused'

    def monitor_behavior(self):
        self.pipeline_TTL.send(self.buffer_TTL.read())

    def init_signal(self):
        signal = self.model.paradigm.signal
        fs = self.iface_behavior.fs
        offset = self.buffer_signal.total_samples_written
        waveform = signal.block.realize(fs, 1.0, 0)
        self.buffer_signal.set(waveform)

    def update_signal(self):
        pending = self.buffer_signal.pending()
        if pending:
            signal = self.model.paradigm.signal
            fs = self.iface_behavior.fs
            offset = self.buffer_signal.total_samples_written
            waveform = signal.block.realize(fs, pending, offset)
            self.buffer_signal.write(waveform)

    def get_ts(self):
        return self.iface_behavior.get_tag('ts')

    def _get_status(self):
        if self.state == 'halted':
            return "Halted"
        if self.state == 'paused':
            return "Experimenter controlled"
        return "Subject controlled"

    def set_primary_attenuation(self, value):
        self.iface_behavior.set_tag('att_A', value)

    def set_secondary_attenuation(self, value):
        self.iface_behavior.set_tag('att_B', value)

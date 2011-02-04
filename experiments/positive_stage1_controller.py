from enthought.traits.api import Property, Str

from tdt import DSPCircuit
from cns.pipeline import deinterleave_bits
from cns.data.h5_utils import append_date_node, append_node
from cns.data.persistence import add_or_update_object

from abstract_experiment_controller import AbstractExperimentController
from pump_controller_mixin import PumpControllerMixin
from positive_stage1_data import PositiveStage1Data

class PositiveStage1Controller(AbstractExperimentController,
        PumpControllerMixin):

    status = Property(Str, depends_on='state')

    def start_experiment(self, info):
        self.init_pump(info)

        self.iface_behavior = DSPCircuit('components/positive-behavior-stage1', 'RZ6')
        self.buffer_signal = self.iface_behavior.get_buffer('signal', 'w')
        self.buffer_TTL = self.iface_behavior.get_buffer('TTL', 'r',
                block_size=24, src_type='int8', dest_type='int8')

        # Set up data files
        exp_node = append_date_node(self.model.store_node,
                                    pre='appetitive_stage1_date_')
        data_node = append_node(exp_node, 'data')
        self.model.data = PositiveStage1Data(store_node=data_node)
        self.model.exp_node = exp_node

        # Set up data collection
        self.init_signal()

        targets = [self.model.data.spout_TTL,
                   self.model.data.override_TTL,
                   self.model.data.pump_TTL, 
                   self.model.data.signal_TTL,
                   self.model.data.free_run_TTL ]

        self.model.data.spout_TTL.fs = self.buffer_TTL.fs
        self.model.data.override_TTL.fs = self.buffer_TTL.fs
        self.model.data.pump_TTL.fs = self.buffer_TTL.fs
        self.model.data.signal_TTL.fs = self.buffer_TTL.fs
        self.model.data.free_run_TTL.fs = self.buffer_TTL.fs

        self.set_attenuation(self.model.paradigm.attenuation)

        self.pipeline_TTL = deinterleave_bits(targets)

        #self.model.data.start_time = datetime.now()
        self.iface_behavior.start()
        self.pause(info)

    def resume(self, info=None):
        self.iface_behavior.set_tag('free_run?', 1)
        self.state = 'running'

    def pause(self, info=None):
        self.iface_behavior.set_tag('free_run?', 0)
        self.state = 'paused'

    def stop_experiment(self, info):
        self.iface_behavior.stop()
        self.state = 'halted'
        #self.model.data.stop_time = datetime.now()
        add_or_update_object(self.model.paradigm, self.model.exp_node, 'paradigm')
        add_or_update_object(self.model.data, self.model.exp_node, 'data')

    def tick_slow(self):
        ts = self.get_ts()
        seconds = int(ts/self.iface_behavior.fs)
        self.monitor_pump()

    def tick_fast(self):
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

    def set_attenuation(self, value):
        self.iface_behavior.set_tag('att_A', value)

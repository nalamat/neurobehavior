from os.path import join
from cns import get_config
from cns.pipeline import deinterleave_bits
from abstract_experiment_controller import AbstractExperimentController

class PositiveStage1Controller(AbstractExperimentController):

    def setup_experiment(self, info):
        circuit = join(get_config('RCX_ROOT'), 'positive-behavior-stage1')
        self.iface_behavior = self.process.load_circuit(circuit, 'RZ6')
        self.buffer_signal = self.iface_behavior.get_buffer('signal', 'w')
        self.buffer_TTL = self.iface_behavior.get_buffer('TTL', 'r',
                block_size=24, src_type='int8', dest_type='int8')
        self.buffer_mic = self.iface_behavior.get_buffer('mic', 'r')
        self.model.data.spout_TTL.fs = self.buffer_TTL.fs
        self.model.data.override_TTL.fs = self.buffer_TTL.fs
        self.model.data.pump_TTL.fs = self.buffer_TTL.fs
        self.model.data.signal_TTL.fs = self.buffer_TTL.fs
        self.model.data.free_run_TTL.fs = self.buffer_TTL.fs
        self.model.data.microphone.fs = self.buffer_mic.fs

        targets = [self.model.data.spout_TTL,
                   self.model.data.override_TTL,
                   self.model.data.pump_TTL, 
                   self.model.data.signal_TTL,
                   self.model.data.free_run_TTL ]
        self.pipeline_TTL = deinterleave_bits(targets)

        self.iface_pump.set_trigger(start='rising', stop='falling')
        self.iface_pump.set_direction('infuse')
        self.iface_pump.set_volume(0)

    def start_experiment(self, info):
        self.invalidate_context()
        self.evaluate_pending_expressions()
        self.update_signal()
        self.iface_behavior.start()
        self.pause()
        self.process.trigger('A', 'high')
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
        self.model.data.microphone.send(self.buffer_mic.read())

    def update_signal(self):
        att, waveform, clip, floor = self.output_primary.realize()
        self.buffer_signal.set(waveform)
        self.iface_behavior.set_tag('att_A', att)
        self.iface_behavior.set_tag('att_B', 120)

    def get_ts(self):
        return self.iface_behavior.get_tag('ts')

    def _get_status(self):
        if self.state == 'halted':
            return "Halted"
        if self.state == 'paused':
            return "Experimenter controlled"
        else:
            return "Subject controlled"

    def _context_updated_fired(self):
        self.invalidate_context()
        self.evaluate_pending_expressions()
        self.update_signal()

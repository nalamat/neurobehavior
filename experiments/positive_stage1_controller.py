from os.path import join
from cns import get_config
from cns.pipeline import deinterleave_bits
from abstract_experiment_controller import AbstractExperimentController
from abstract_experiment_controller import ExperimentToolBar
from enthought.traits.api import Any, Instance

from enthought.savage.traits.ui.svg_button import SVGButton

from traitsui.api import Item, View, HGroup, spring
from cns.widgets.icons import icons

class PositiveStage1ToolBar(ExperimentToolBar):

    size    = 24, 24
    kw      = dict(height=size[0], width=size[1], action=True)

    manual = SVGButton('Manual', filename=icons['pause'],
                        tooltip='Manual control', **kw)

    automatic  = SVGButton('Automatic', filename=icons['resume'],
                           tooltip='Auto mode', **kw)
    
    item_kw = dict(show_label=False)
    traits_view = View(
            HGroup(Item('apply',
                        enabled_when="object.handler.pending_changes"),
                   Item('revert',
                        enabled_when="object.handler.pending_changes",),
                   Item('start',
                        enabled_when="object.handler.state=='halted'",),
                   '_',
                   Item('manual', 
                        enabled_when="object.handler.state=='running'",
                        **item_kw),
                   Item('automatic',
                        enabled_when="object.handler.state=='paused'",
                        **item_kw),
                   Item('stop',
                        enabled_when="object.handler.state in " +\
                                     "['running', 'paused', 'manual']",),
                   spring,
                   springy=True,
                   show_labels=False,
                   ),
            kind='subpanel',
            )

class PositiveStage1Controller(AbstractExperimentController):

    pipeline_TTL = Any

    toolbar = Instance(PositiveStage1ToolBar, (), toolbar=True)

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
        self.update_waveform()
        self.iface_behavior.start()
        self.manual()
        self.process.trigger('A', 'high')
        self.tasks.append((self.monitor_pump, 5))
        self.tasks.append((self.monitor_behavior, 1))

    def automatic(self, info=None):
        self.iface_behavior.set_tag('free_run?', 1)
        self.state = 'running'

    def manual(self, info=None):
        self.iface_behavior.set_tag('free_run?', 0)
        self.state = 'paused'

    def monitor_behavior(self):
        self.pipeline_TTL.send(self.buffer_TTL.read())
        self.model.data.microphone.send(self.buffer_mic.read())

    def get_ts(self):
        return self.iface_behavior.get_tag('ts')

    def _get_status(self):
        if self.state == 'halted':
            return "Halted"
        if self.state == 'paused':
            return "Experimenter controlled"
        else:
            return "Subject controlled"

    def context_updated(self):
        self.update_waveform()

    def update_waveform(self):
        self.invalidate_context()
        self.evaluate_pending_expressions()
        speaker = self.get_current_value('speaker')

        if speaker == 'primary':
            calibration = self.cal_primary
        else:
            calibration = self.cal_secondary

        waveform, attenuation = self.compute_waveform(calibration)
        self.buffer_signal.set(waveform)

        if speaker == 'primary':
            self.iface_behavior.set_tag('att_A', attenuation)
            self.iface_behavior.set_tag('att_B', 120)
        else:
            self.iface_behavior.set_tag('att_A', 120)
            self.iface_behavior.set_tag('att_B', attenuation)


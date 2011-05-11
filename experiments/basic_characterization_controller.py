from os.path import join
from cns import RCX_ROOT
from tdt import DSPCircuit

from abstract_experiment_controller import AbstractExperimentController
from abstract_experiment_controller import ExperimentToolBar

from enthought.traits.api import Instance
from enthought.traits.ui.api import View, HGroup, spring, Item

class BasicCharacterizationToolbar(ExperimentToolBar):

    traits_view = View(
            HGroup(
                Item('start', enabled_when="object.handler.state=='halted'"),
                Item('resume', enabled_when="object.handler.state=='paused'"),
                Item('pause', enabled_when="object.handler.state=='running'"),
                spring,
                show_labels=False,
                springy=True,
                ),
            )

class BasicCharacterizationController(AbstractExperimentController):

    toolbar = Instance(BasicCharacterizationToolbar, (), toolbar=True)

    def setup_experiment(self, info):
        circuit = join(RCX_ROOT, 'basic_audio')
        self.iface_audio = self.process.load_circuit(circuit, 'RZ6')

    def start_experiment(self, info):
        #self.init_paradigm(self.model.paradigm)
        self.iface_audio.trigger('A', 'high')
        self.state = 'running'

    def pause(self, info):
        self.iface_audio.trigger('A', 'low')
        self.state = 'paused'

    def resume(self, info):
        self.iface_audio.trigger('A', 'high')
        self.state = 'running'

    def set_token_duration(self, value):
        self.iface_audio.cset_tag('token_dur_n', value, 's', 'n')

    def set_trial_duration(self, value):
        self.iface_audio.cset_tag('trial_dur_n', value, 's', 'n')

    def set_center_frequency(self, value):
        self.iface_audio.set_tag('t_freq', value)
        self.update_filter_settings()

    def set_bandwidth_ratio(self, value):
        if value == 0:
            self.iface_audio.set_tag('selector', 0)
        else:
            self.iface_audio.set_tag('selector', 1)
        self.update_filter_settings()

    def update_filter_settings(self):
        cf = self.model.paradigm.center_frequency
        br = self.model.paradigm.bandwidth_ratio
        bw = cf*br
        flow, fhigh = cf-bw/2.0, cf+bw/2.0
        self.iface_audio.set_tag('FiltHP', flow)
        self.iface_audio.set_tag('FiltLP', fhigh)

    def set_modulation_frequency(self, value):
        self.iface_audio.set_tag('m_freq', value)

    def set_modulation_depth(self, value):
        amplitude = value/2.0
        offset = 1-amplitude
        print amplitude, offset
        self.iface_audio.set_tag('m_amplitude', amplitude)
        self.iface_audio.set_tag('m_shift', offset)

    def get_ts(self):
        return -1

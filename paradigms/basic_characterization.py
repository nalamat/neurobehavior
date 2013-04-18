from traits.api import Instance, on_trait_change, Range, Button, Any, HasTraits
from traitsui.api import View, VGroup, Item, HGroup, spring
from cns.channel import FileChannel
from chaco.api import DataRange1D, LinearMapper
from cns.chaco_exts.rms_channel_plot import RMSChannelPlot

from os.path import join
from cns import get_config

from experiments.abstract_experiment import AbstractExperiment
from experiments.abstract_experiment_data import AbstractExperimentData
from experiments.abstract_experiment_controller import AbstractExperimentController
from experiments.abstract_experiment_controller import ExperimentToolBar
from experiments.abstract_experiment_paradigm import AbstractExperimentParadigm

class BasicCharacterizationToolbar(ExperimentToolBar):

    traits_view = View(
            HGroup(
                Item('start', enabled_when="object.handler.state=='halted'"),
                spring,
                show_labels=False,
                springy=True,
                ),
            )

class Controller(AbstractExperimentController):

    toolbar = Instance(BasicCharacterizationToolbar, (), toolbar=True)
    iface_audio = Instance('tdt.DSPCircuit')
    buffer_mic = Instance('tdt.DSPBuffer')

    def _iface_audio_default(self):
        circuit = join(get_config('RCX_ROOT'), 'basic_audio')
        return self.process.load_circuit(circuit, 'RZ6')

    def _buffer_mic_default(self):
        mic = self.iface_audio.get_buffer('mic', 'r')
        self.model.data.microphone.fs = mic.fs
        return mic

    def monitor_mic(self):
        self.model.data.microphone.send(self.buffer_mic.read())

    def setup_experiment(self, info):
        pass

    def start_experiment(self, info):
        self.iface_audio.trigger('A', 'high')
        self.state = 'running'
        self.tasks.append((self.monitor_mic, 1))

    def pause(self, info):
        self.iface_audio.trigger('A', 'low')
        self.state = 'paused'

    def resume(self, info):
        self.iface_audio.trigger('A', 'high')
        self.state = 'running'

    @on_trait_change('model.paradigm.token_duration')
    def set_token_duration(self, value):
        self.iface_audio.cset_tag('token_dur_n', value, 's', 'n')

    @on_trait_change('model.paradigm.trial_duration')
    def set_trial_duration(self, value):
        self.iface_audio.cset_tag('trial_dur_n', value, 's', 'n')

    @on_trait_change('model.paradigm.center_frequency')
    def set_center_frequency(self, value):
        self.iface_audio.set_tag('t_freq', value)
        self.update_filter_settings()

    @on_trait_change('model.paradigm.bandwidth_ratio')
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

    @on_trait_change('model.paradigm.modulation_frequency')
    def set_modulation_frequency(self, value):
        self.iface_audio.set_tag('m_freq', value)

    @on_trait_change('model.paradigm.modulation_depth')
    def set_modulation_depth(self, value):
        amplitude = value/2.0
        offset = 1-amplitude
        self.iface_audio.set_tag('m_amplitude', amplitude)
        self.iface_audio.set_tag('m_shift', offset)

    @on_trait_change('model.paradigm.primary_attenuation')
    def set_primary_attenuation(self, value):
        self.iface_audio.set_tag('att_A', value)

    @on_trait_change('model.paradigm.secondary_attenuation')
    def set_secondary_attenuation(self, value):
        self.iface_audio.set_tag('att_B', value)

    def get_ts(self):
        return -1

class Paradigm(AbstractExperimentParadigm):
    
    mute_speakers = Button
    swap_speakers = Button
    _old_speaker_settings = Any(None)
    
    def _mute_speakers_fired(self):
        if self._old_speaker_settings is None:
            primary = self.primary_attenuation
            secondary = self.secondary_attenuation
            self._old_speaker_settings = primary, secondary
            self.primary_attenuation = 120
            self.secondary_attenuation = 120
        else:
            primary, secondary = self._old_speaker_settings
            self.primary_attenuation = primary
            self.secondary_attenuation = secondary
            self._old_speaker_settings = None
            
    def _swap_speakers_fired(self):
        primary = self.primary_attenuation
        secondary = self.secondary_attenuation
        self.primary_attenuation = secondary
        self.secondary_attenuation = primary

    primary_attenuation     = Range(0, 120, 120)
    secondary_attenuation   = Range(0, 120, 120)

    token_duration          = Range(0.01, 10.0, 1.0)
    trial_duration          = Range(0.01, 20.0, 2.0)
    center_frequency        = Range(100, 50e3, 5e3)
    bandwidth_ratio         = Range(0.0, 2, 0.3)
    modulation_frequency    = Range(0.0, 100, 5.0)
    modulation_depth        = Range(0.0, 1.0, 0.0)

    traits_view = View(
            VGroup(
                HGroup(
                    Item('mute_speakers', show_label=False),
                    Item('swap_speakers', show_label=False),
                    'primary_attenuation',
                    'secondary_attenuation',
                    ),
                'trial_duration',
                'token_duration',
                Item('center_frequency'),
                'bandwidth_ratio',
                'modulation_frequency',
                'modulation_depth'
                ),
            width=400,
            title='Positive paradigm editor',
            )

class Experiment(AbstractExperiment):

    def _add_experiment_plots(self, index_mapper, container, alpha=0.25):
        value_range = DataRange1D(low_setting=-20, high_setting=80)
        value_mapper = LinearMapper(range=value_range)
        plot = RMSChannelPlot(source=self.data.microphone,
                index_mapper=index_mapper, value_mapper=value_mapper,
                line_color=(0.2, 0.2, 0.2, 0.50))
        container.add(plot)

    traits_group = VGroup(
            Item('handler.toolbar', style='custom'),
            Item('paradigm', style='custom'),
            show_labels=False,
            )

class Data(AbstractExperimentData):

    microphone = Instance(FileChannel)

    def _microphone_default(self):
        return FileChannel(node=self.store_node, name='microphone',
                dtype='float32')

node_name = 'BasicCharacterizationExperiment'

from enthought.traits.api import Instance
from enthought.traits.ui.api import View, VGroup, Item, Include
from experiments.evaluate import Expression
from os.path import join
from cns import get_config
from cns.signal import am_eq_power, am_eq_phase
import numpy as np

from experiments.abstract_aversive_experiment import AbstractAversiveExperiment
from experiments.abstract_aversive_controller import AbstractAversiveController
from experiments.abstract_aversive_paradigm import AbstractAversiveParadigm
from experiments.aversive_data import AversiveData

from experiments.cl_controller_mixin import CLControllerMixin
from experiments.cl_paradigm_mixin import CLParadigmMixin
from experiments.cl_experiment_mixin import CLExperimentMixin
from experiments.aversive_cl_data_mixin import AversiveCLDataMixin

from experiments.pump_controller_mixin import PumpControllerMixin
from experiments.pump_paradigm_mixin import PumpParadigmMixin
from experiments.pump_data_mixin import PumpDataMixin

class Controller(
        CLControllerMixin,
        PumpControllerMixin,
        AbstractAversiveController):

    def initial_setting(self):
        return self.nogo_setting()

    def _setup_circuit(self):
        # AversiveFMController needs to change the initialization sequence a
        # little (i.e. it needs to use different microcode and the microcode
        # does not contain int and trial buffers).
        circuit = join(get_config('RCX_ROOT'), 'aversive-behavior-FMAM')
        self.iface_behavior = self.process.load_circuit(circuit, 'RZ6')
        self.buffer_TTL = self.iface_behavior.get_buffer('TTL', 'r',
                src_type='int8', dest_type='int8', block_size=24)
        self.buffer_contact = self.iface_behavior.get_buffer('contact', 'r',
                src_type='int8', dest_type='float32', block_size=24)
        self.buffer_spout_start = self.iface_behavior.get_buffer('spout/', 'r',
                src_type='int32', block_size=1)
        self.buffer_spout_end = self.iface_behavior.get_buffer('spout\\', 'r',
                src_type='int32', block_size=1)

    def update_trial(self):
        pass

    def update_intertrial(self):
        pass

    def set_fm_depth(self, value):
        self.iface_behavior.set_tag('fm_depth', value)

    def set_fm_freq(self, value):
        self.iface_behavior.set_tag('fm_freq', value)

    def set_fm_direction(self, value):
        # This is linked to a Tone component that generates a sinusoid wave that
        # controls the instantaneous frequency of actual tone.  To get a
        # positive upsweep in frequency, set the starting phase to 0.  To get a
        # negative downsweep in frequency, set the starting phase to pi.  In
        # either case, sin(phase) **must** evaluate to 0 to ensure there are no
        # discontinuities in transitioning from the intertrial to trial signal.
        if value == 'positive':
            self.iface_behavior.set_tag('fm_phase', 0)
        elif value == 'negative':
            self.iface_behavior.set_tag('fm_phase', np.pi)

    def set_am_direction(self, value):
        self._update_am()

    def set_am_depth(self, value):
        self._update_am()

    def set_am_freq(self, value):
        self.iface_behavior.set_tag('am_freq', value)

    def _update_am(self):
        am_direction = self.get_current_value('am_direction')
        am_depth = self.get_current_value('am_depth')

        am_amplitude = am_depth/2.0
        am_shift = 1-am_amplitude
        am_phase = am_eq_phase(am_depth, am_direction)
        am_sf = 1.0/am_eq_power(am_depth)

        self.iface_behavior.set_tag('am_amplitude', am_amplitude)
        self.iface_behavior.set_tag('am_shift', am_shift)
        self.iface_behavior.set_tag('am_phase', am_phase)
        self.iface_behavior.set_tag('am_sf', am_sf)

    def set_fc(self, value):
        coerced_value = self.cal_primary.get_nearest_frequency(value)
        self.iface_behavior.set_tag('fc', coerced_value)
        mesg = 'Coercing {} Hz to nearest calibrated frequency of {} Hz'
        self.notify(mesg.format(value, coerced_value))
        self.set_current_value('fc', coerced_value)

    def set_level(self, value):
        speaker = self.get_current_value('speaker')
        fc = self.get_current_value('fc')

        if speaker == 'primary':
            att = self.cal_primary.get_attenuation(fc, value)
            self.iface_behavior.set_tag('att1', att)
            self.iface_behavior.set_tag('att2', 120.0)
        elif speaker == 'secondary':
            att = self.cal_secondary.get_attenuation(fc, value)
            self.iface_behavior.set_tag('att2', att)
            self.iface_behavior.set_tag('att1', 120.0)
        else:
            raise ValueError, 'Unsupported speaker mode %r' % speaker

class Paradigm(
        AbstractAversiveParadigm, 
        PumpParadigmMixin,
        CLParadigmMixin,
        ):

    editable_nogo = False
    repeat_fa = False
    go_probability = 'h_uniform(c_safe, 3, 7)'

    kw = {'context': True, 'log': True}

    fc = Expression(4000, label='Carrier frequency (Hz)', **kw)
    level = Expression(0.0, label='Level (dB SPL)', **kw)
    fm_depth = Expression(200, label='FM depth (Hz)', **kw)
    fm_freq = Expression(5, label='FM frequency (Hz)', **kw)
    fm_direction = Expression("'positive'", **kw)
    am_depth = Expression(0, label='AM depth (Hz)', **kw)
    am_freq = Expression('fm_freq', label='AM frequency (Hz)', **kw)
    am_direction = Expression("'positive'", **kw)

    signal_group = VGroup(
            'fc',
            'level',
            'fm_depth',
            'fm_freq',
            'fm_direction',
            'am_depth',
            'am_freq',
            'am_direction',
            show_border=True, 
            label='FM/AM parameters')

    traits_view = View(
            VGroup(
                VGroup(
                    VGroup(
                        Item('go_probability', label='Warn probability'),
                        Item('go_setting_order', label='Warn setting order'),
                        ),
                    Include('cl_trial_setting_group'),
                    label='Constant limits',
                    show_border=True,
                    ),
                Include('abstract_aversive_paradigm_group'),
                label='Paradigm',
                ),
            VGroup(
                Include('speaker_group'),
                Include('signal_group'),
                label='Signal',
                ),
            )

class Data(AversiveData, AversiveCLDataMixin, PumpDataMixin):
    pass

class Experiment(AbstractAversiveExperiment, CLExperimentMixin):

    data = Instance(Data, ())
    paradigm = Instance(Paradigm, ())

node_name = 'AversiveFMCLExperiment'

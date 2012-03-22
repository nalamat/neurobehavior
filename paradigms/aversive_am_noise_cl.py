'''
Aversive AM noise
-----------------
.. moduleauthor:: Brad Buran <bburan@alum.mit.edu>

TODO: description
'''

from enthought.traits.api import Instance, Any, Int
from enthought.traits.ui.api import View, VGroup, Item, Include
from experiments.evaluate import Expression

import time 
import numpy as np
from cns import signal

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

import logging
log = logging.getLogger(__name__)

class Controller(
        CLControllerMixin,
        PumpControllerMixin,
        AbstractAversiveController):

    random_generator = Any
    random_seed = Int(-1, context=True, log=True, immediate=True)

    def setup_experiment(self, info):
        super(Controller, self).setup_experiment(info)
        # Generate a random seed
        self.random_seed = int(time.time())
        self.random_generator = np.random.RandomState(self.random_seed)
        node = info.object.experiment_node
        node._v_attrs['intertrial_noise_random_seed'] = self.random_seed
        self.random_generator = np.random.RandomState(self.random_seed)

    def initial_setting(self):
        return self.nogo_setting()

    def generate_trial_waveform(self):
        # Use BBN
        seed = self.get_current_value('seed')
        depth = self.get_current_value('modulation_depth')
        direction = self.get_current_value('modulation_direction')
        fm = self.get_current_value('fm')
        duration = self.get_current_value('trial_duration')

        t = signal.time(self.iface_behavior.fs, duration)

        # Save the actual seed that's used to generate the trial waveform
        if seed == -1:
            seed = int(time.time())
            self.set_current_value('seed', seed)

        # Do not use the self.random_generator for generating the seed.  This
        # generator is for use only for generating the intertrial waveform.
        state = np.random.RandomState(seed)
        waveform = state.uniform(low=-1, high=1, size=len(t))

        # Since we are drawing samples from a uniform distribution and we wish
        # to normalize for the RMS voltage, we need to divide by 0.5 which is
        # the RMS value of the waveform.  We could recompute the RMS value on
        # each cycle; however, I think it's better to use the same value each
        # time.  The RMS of the waveform over time will compute to 0.5 (because
        # the samples are unformly distributed between -1 and 1).
        waveform = waveform/0.5
        eq_phase = signal.sam_eq_phase(depth, direction)
        eq_power = signal.sam_eq_power(depth)
        envelope = depth/2.0 * np.cos(2*np.pi*fm*t+eq_phase) + 1 - depth/2.0
        envelope *= 1/eq_power
        return waveform*envelope

    def set_attenuation(self, attenuation):
        self._update_attenuation()

    def set_speaker(self, speaker):
        self._update_attenuation()

    def _update_attenuation(self):
        attenuation = self.get_current_value('attenuation')
        speaker = self.get_current_value('speaker')
        if speaker == 'primary':
            self.set_attenuations(attenuation, 120)
        elif speaker == 'secondary':
            self.set_attenuations(120, attenuation)
        else:
            raise ValueError, 'Unsupported speaker mode %r' % speaker

    def update_intertrial(self):
        samples = self.buffer_int.available()
        waveform = self.random_generator.uniform(low=-1, high=1, size=samples)
        # Normalize for RMS (see comment above)
        waveform = waveform/0.5
        self.buffer_int.write(waveform)

    def update_trial(self):
        waveform = self.generate_trial_waveform()
        log.debug('Uploading %d samples to the trial buffer', len(waveform))
        self.buffer_trial.set(waveform)

class Paradigm(
        AbstractAversiveParadigm, 
        PumpParadigmMixin,
        CLParadigmMixin,
        ):

    # Override settings 
    repeat_fa = False
    go_probability = 'h_uniform(c_safe, 3, 7)'
    modulation_onset = 0.0
    modulation_direction = "'positive' if toss() else 'negative'"

    kw = {'context': True, 'store': 'attribute', 'log': True}

    fm = Expression(5, label='Modulation frequency (Hz)', **kw)
    attenuation = Expression(60.0, label='Attenuation (dB)', **kw)
    seed = Expression(-1, label='Noise seed (trial only)', **kw)
    modulation_depth = Expression(1.0, label='Modulation depth (frac)', **kw)
    modulation_direction = Expression("'positive'", 
            label='Initial modulation direction', **kw)

    # This defines what is visible via the GUI
    signal_group = VGroup(
            'speaker',
            'fm',
            'modulation_depth',
            'attenuation',
            'modulation_direction',
            'seed',
            label='Signal',
            show_border=True,
            )

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

    data = Instance(Data, (), store='child')
    paradigm = Instance(Paradigm, (), store='child')

node_name = 'AversiveAMNoiseExperiment'

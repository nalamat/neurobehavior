from enthought.traits.api import Instance
from enthought.traits.ui.api import View, Include, VGroup, Item, Include
from enthought.enable.api import Component, ComponentEditor
from experiments.evaluate import Expression

import numpy as np
from cns import signal

from experiments import (
        # Controller and mixins
        AbstractAversiveController,
        ConstantLimitsControllerMixin, 
        PumpControllerMixin,
        AversiveAMNoiseControllerMixin,

        # Paradigm and mixins
        AbstractAversiveParadigm,
        ConstantLimitsParadigmMixin,
        PumpParadigmMixin,
        AMBBNParadigmMixin,

        # The experiment
        AbstractAversiveExperiment,
        ConstantLimitsExperimentMixin,

        # Data
        AversiveData,
        AversiveConstantLimitsDataMixin
        )

class Controller(
	# Order of these classes are important for determining the method
	# resolution order (i.e. the order in which each of the class
	# definitions is checked for the method being requested).
        ConstantLimitsControllerMixin,
        PumpControllerMixin,
        AbstractAversiveController):

    def initial_setting(self):
        return self.nogo_setting()

    def _generate_trial_waveform(self):
        # Use BBN
        level = self.get_current_value('level')
        seed = self.get_current_value('seed')
        onset = self.get_current_value('modulation_onset')
        depth = self.get_current_value('modulation_depth')
        direction = self.get_current_value('modulation_direction')
        fm = self.get_current_value('fm')
        duration = self.get_current_value('duration')

        t = signal.time(self.iface_behavior.fs, duration)

        state = np.random.RandomState(seed)
        waveform = state.uniform(low=-1, high=1, size=len(t))
        rms = signal.rms(waveform)
        waveform = amplitude/rms*samples

        eq_phase = signals.am_eq_phase(depth, direction)
        eq_power = signals.am_eq_power(depth)
        envelope = depth/2.0 * np.cos(2*np.pi*fm+eq_phase) + 1 - depth/2.0
        envelope *= 1/eq_power
        return waveform*envelope

    def set_speaker_equalize(self, value):
        if value:
            raise NotImplementedError, "Cannot equalize signal"
    
    def update_intertrial(self):
        samples = self.buffer_int.available()
        state = np.random.RandomState() # Seed will be "random"
        waveform = state.uniform(low=-1, high=1, size=samples)
        rms = signal.rms(waveform)
        waveform = amplitude/rms*waveform
        self.buffer_int.write(waveform)

    def update_trial(self):
        speaker = self.get_current_value('speaker')
        if speaker == 'primary':
            waveform, att1 = self._generate_trial_waveform(self.cal_primary)
            att2 = 120.0
        elif speaker == 'secondary':
            waveform, att2 = self._generate_trial_waveform(self.cal_secondary)
            att1 = 120.0
        else:
            raise ValueError, 'Unsupported speaker {}'.format(speaker)
        self.set_attenuations(att1, att2, mode='full')
        self.buffer_trial.set(waveform)

class Paradigm(
        AbstractAversiveParadigm, 
        PumpParadigmMixin,
        ConstantLimitsParadigmMixin,
        AMBBNParadigmMixin,
        ):

    # Override settings 
    repeat_fa = False
    go_probability = 'h_uniform(c_safe, 3, 7)'
    modulation_onset = 0.0
    modulation_direction = "'positive' if toss() else 'negative'"

    kw = {'context': True, 'store': 'attribute', 'log': True}

    fm = Expression(5, label='Modulation frequency (Hz)', **kw)
    level = Expression(60.0, label='Spectrum Level (dB SPL)', **kw)
    seed = Expression(-1, label='Noise seed', **kw)
    modulation_depth = Expression(1.0, label='Modulation depth (frac)', **kw)
    modulation_direction = Expression("'positive'", 
            label='Initial modulation direction', **kw)

    # This defines what is visible via the GUI
    signal_group = VGroup(
            'fm',
            'modulation_depth',
            'level',
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

class Data(AversiveData, AversiveConstantLimitsDataMixin):
    pass

class Experiment(AbstractAversiveExperiment, ConstantLimitsExperimentMixin):

    data = Instance(Data, (), store='child')
    paradigm = Instance(Paradigm, (), store='child')

node_name = 'AversiveAMNoiseExperiment'

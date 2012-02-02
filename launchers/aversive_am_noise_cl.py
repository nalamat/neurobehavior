from enthought.traits.api import Instance
from enthought.traits.ui.api import View, Include, VGroup, Item, Include
from enthought.enable.api import Component, ComponentEditor
from experiments.evaluate import Expression

import neurogen.block_definitions as blocks
from neurogen.sink import Sink
import numpy as np

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
        ConstantLimitsControllerMixin,
        PumpControllerMixin,
        AbstractAversiveController):

    def initial_setting(self):
        return self.nogo_setting()

    int_carrier     = Instance(blocks.Block)
    trial_carrier   = Instance(blocks.Block)
    trial_modulator = Instance(blocks.Block)
    output_int      = Instance(Sink)
    output_trial    = Instance(Sink)

    def _output_int_default(self):
        return Sink(token=self.int_carrier.waveform, fs=self.iface_behavior.fs,
                calibration=self.cal_primary)

    def _output_trial_default(self):
        return Sink(token=self.trial_modulator.waveform,
                fs=self.iface_behavior.fs, calibration=self.cal_primary)

    def set_speaker_equalize(self, value):
        self.output_trial.equalize = value
        self.output_int.equalize = value
    
    def set_level(self, value):
        self.int_carrier.level = value
        self.trial_carrier.level = value

    def _trial_carrier_default(self):
        return blocks.BroadbandNoise()

    def _int_carrier_default(self):
        return blocks.BroadbandNoise()

    def _trial_modulator_default(self):
        return blocks.SAM(token=self.trial_carrier.waveform, 
                equalize_power=True,
                equalize_phase=True)
        
    def set_seed(self, value):
        self.int_carrier.seed = value
        self.trial_carrier.seed = value

    def set_modulation_onset(self, value):
        self.trial_modulator.delay = value

    def set_modulation_depth(self, value):
        self.trial_modulator.depth = value

    def set_modulation_direction(self, value):
        self.trial_modulator.equalize_direction = value

    def set_trial_duration(self, value):
        super(AversiveAMNoiseControllerMixin, self).set_trial_duration(value)
        self.output_int.duration = value
        self.output_trial.duration = value

    def set_fm(self, value):
        self.trial_modulator.frequency = value

    def update_intertrial(self):
        samples = self.buffer_int.available()
        att, waveform, clip, floor = self.output_int.realize_samples(samples)
        self.buffer_int.write(waveform)

    def update_trial(self):
        speaker = self.get_current_value('speaker')
        if speaker == 'primary':
            self.output_trial.calibration = self.cal_primary
            att1, waveform, clip, floor = self.output_trial.realize()
            att2 = 120.0
        elif speaker == 'secondary':
            self.output_trial.calibration = self.cal_secondary
            att2, waveform, clip, floor = self.output_trial.realize()
            att1 = 120.0
        else:
            raise ValueError, 'Unsupported speaker mode %r' % speaker

        self.set_attenuations(att1, att2, mode='full')
        self.buffer_trial.set(waveform)

class Paradigm(
        AbstractAversiveParadigm, 
        PumpParadigmMixin,
        ConstantLimitsParadigmMixin,
        AMBBNParadigmMixin,
        ):

    repeat_fa = False
    go_probability = 'h_uniform(c_safe, 3, 7)'
    modulation_onset = 0.0
    modulation_direction = "'positive' if toss() else 'negative'"

    kw = {'context': True, 'store': 'attribute', 'log': True}

    modulation_onset = Expression('uniform(0.2, 0.4)', label='Modulation onset (s)')
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
            'modulation_onset',
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

import numpy as np

from enthought.traits.api import Instance
from enthought.traits.ui.api import View, VGroup, Item, Include
from experiments.evaluate import Expression

from cns.signal import time, generate_envelope

from experiments import (
        # Controller and mixins
        AbstractAversiveController,
        ConstantLimitsControllerMixin, 
        PumpControllerMixin,

        # Paradigm and mixins
        AbstractAversiveParadigm,
        ConstantLimitsParadigmMixin,
        PumpParadigmMixin,

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

    def set_fc(self, value):
        # Ensure that the requested carrier frequency falls on a calibrated
        # frequency so that we can ensure the calibration/output is accurate
        # even if the frequency falls within or near a notch.
        coerced_value = self.cal_primary.get_nearest_frequency(value)
        self.iface_behavior.set_tag('fc', coerced_value)
        mesg = 'Coercing {} Hz to nearest calibrated frequency of {} Hz'
        self.notify(mesg.format(value, coerced_value))
        self.set_current_value('fc', coerced_value)

    def _compute_waveform(self, calibration):
        # Gather the variables we need
        fs = self.buffer_trial.fs
        fc = self.get_current_value('frequency')
        ramp_duration = self.get_current_value('ramp_duration')
        duration = self.get_current_value('trial_duration')
        level = self.get_current_value('level')
        amplitude = 1 # Signal is not calibrated right now
        phase = 0
        ramp_n = int(ramp_duration*fs)

        att = calibration.get_attenuation(fc, level)
        att = min(att, 120)

        t = time(fs, duration)
        y = amplitude*np.sin(2*np.pi*fc*t+phase)
        envelope = generate_envelope(len(y), ramp_n)
        return y*envelope, att

    def update_trial(self):
        speaker = self.get_current_value('speaker')
        if speaker == 'primary':
            waveform, att1 = self._compute_waveform(self.cal_primary)
            att2 = 120.0
        elif speaker == 'secondary':
            waveform, att2 = self._compute_waveform(self.cal_secondary)
            att1 = 120.0
        else:
            raise ValueError, 'Unsupported speaker mode %r' % speaker
        self.iface_behavior.set_tag('att1', att1)
        self.iface_behavior.set_tag('att2', att2)
        self.buffer_trial.set(waveform)

    def update_intertrial(self):
        pass

class Paradigm(
        AbstractAversiveParadigm, 
        PumpParadigmMixin,
        ConstantLimitsParadigmMixin,
        ):

    kw = {'context': True, 'store': 'attribute', 'log': True}
    ramp_duration = Expression(0.0025, label='Ramp duration (s)', **kw)
    frequency = Expression(4000, label='Frequency (Hz)', **kw)
    level = Expression(0.0, label='Level (dB SPL)', **kw)

    signal_group = VGroup(
            'frequency',
            'ramp_duration',
            'level',
            show_border=True, 
            label='Tone parameters')

    repeat_fa = False
    go_probability = 'h_uniform(c_safe, 3, 7)'

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

node_name = 'AversiveDTExperiment'

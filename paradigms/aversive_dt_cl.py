import numpy as np

from traits.api import List, CFloat, Instance, Any, Bool, Float
from traitsui.api import VGroup, Item, Label, TabularEditor, View, Include
from traitsui.tabular_adapter import TabularAdapter
from experiments.evaluate import Expression

from cns import signal as wave

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

from cns import get_config

import logging
log = logging.getLogger(__name__)

MAX_VRMS = get_config('MAX_SPEAKER_DAC_VOLTAGE')

class Controller(
        CLControllerMixin,
        PumpControllerMixin,
        AbstractAversiveController):

    # Scaling factor used for the waveform.  Must call it "dt" because the
    # superclass already defines a waveform_sf that is overwritten by the
    # superclass trigger_next method.
    kw = {'context': True, 'log': True, 'immediate': True}
    dt_waveform_sf  = Float(np.nan, label='DT scaling factor', **kw)
    dt_waveform_error = Bool(False, label='DT waveform error?', **kw)

    def initial_setting(self):
        return self.nogo_setting()

    def update_trial(self):
        speaker = self.get_current_value('speaker')
        if speaker == 'primary':
            hw_atten = self.hw_att1
            calibration = self.cal_primary
        elif speaker == 'secondary':
            hw_atten = self.hw_att2
            calibration = self.cal_secondary
        else:
            raise ValueError, 'Unsupported speaker mode %r' % speaker

        # Attenuation is handled by the set_expected_speaker_range
        waveform = self.compute_waveform(calibration, hw_atten)
        self.buffer_trial.set(waveform)

    def update_intertrial(self):
        pass

    # This paradigm demonstrates how one can cache some of the computations
    # underlying the waveform generation.  Essentially we cache the "pieces" of
    # the waveform (e.g. the token and envelope) and load the cached waveform
    # each time we need to generate and upload the trial token.

    def set_trial_duration(self, value):
        # Note that as soon as we set self._time_valid to False,
        # self.__time_valid_changed(False) will be executed which sets
        # self._token_valid and self._envelope_valid to False.  This is an
        # Enthought Traits feature.
        self._time_valid = False

        # Be sure to call superclass so it can do its stuff
        super(Controller, self).set_trial_duration(value)

    #########################################################################
    # Fixed attenuation logic
    #########################################################################

    # This will *only* be called when the user updates the
    # expected_speaker_range list via the GUI and hits the "apply" button.  We
    # want to ensure that the waveform can be scaled up to 7 volts peak-to-peak.
    def set_expected_speaker_range(self, value):
        att1 = self.cal_primary.get_best_attenuation(value, voltage=MAX_VRMS)
        att2 = self.cal_secondary.get_best_attenuation(value, voltage=MAX_VRMS)
        log.debug('Best attenuations are %.2f and %.2f', att1, att2)
        self.set_attenuations(att1, att2)

    #########################################################################
    # Cached waveforms to speed up computation
    #########################################################################

    _time = Any
    _token = Any
    _envelope = Any

    def _get_time(self):
        if not self._time_valid:
            log.debug('recomputing _time')
            duration = self.get_current_value('trial_duration')
            self._time = wave.time(self.iface_behavior.fs, duration)
            self._time_valid = True
        return self._time

    def _get_token(self):
        if not self._token_valid:
            log.debug('recomputing _token')
            fc = self.get_current_value('fc')
            t = self._get_time()
            self._token = np.sin(2*np.pi*fc*t)
            self._token_valid = True
        return self._token

    def _get_envelope(self):
        if not self._envelope_valid:
            log.debug('recomputing _envelope')
            rise_time = self.get_current_value('rise_fall_time')
            ramp_n = int(rise_time*self.iface_behavior.fs)
            t = self._get_time()
            self._envelope = wave.generate_envelope(len(t), ramp_n)
            self._envelope_valid = True
        return self._envelope

    #########################################################################
    # Boolean flags indicating whether or not cached data is valid
    #########################################################################

    _time_valid = Bool(False)
    _token_valid = Bool(False)
    _envelope_valid = Bool(False)

    # All HasTraits classes will call the function _<attribute_name>_changed
    # whenever the value of the attribute changes.  If the function does not
    # exist, nothing is done.  Note the double underscore in the function
    # definition due to the fact that the attribute name, _time_valid, starts
    # with a single underscore.
    def __time_valid_changed(self, value):
        if not value:
            log.debug('_time is invalid, invalidating _token and _envelope')
            self._token_valid = False
            self._envelope_valid = False

    #########################################################################
    # Trigger recomputation of cached time/token/envelope as needed
    #########################################################################

    def set_rise_fall_time(self, value):
        self._envelope_valid = False

    def set_fc(self, value):
        # Both cal_primary and cal_secondary should (hopefully) have the same
        # calibrated set of frequencies
        coerced_value = self.cal_primary.get_nearest_frequency(value)
        self.set_current_value('fc', coerced_value)

        # Let's let the user know, just in case this is something they care
        # about.
        mesg = 'Coercing {} Hz to nearest calibrated frequency of {} Hz'
        self.notify(mesg.format(value, coerced_value))

        # Currently the logic which calls the set_<parameter_name> functions
        # checks to see what value the user has specified for the parameter.  In
        # this case, the following steps occur:
        # * The user has specified 12000 Hz as the arrier frequency via the GUI
        # * self.set_fc(12000) is executed and the value gets coerced to 12007
        # * On the next trial, the requested value is (still) 12000 because
        #   that's what was requested via the GUI.  This value is compared with
        #   the value of the previous trial, which was coerced to 12007.  Since
        #   12007 != 12000, it looks like the value has changed so
        #   self.set_fc(12000) is called.
        # * self.set_fc(12000) coerces the value to 12007.  Since the carrier
        #   frequency used for computing the waveform hasn't changed, there's no
        #   need to mark the token as invalid.  But, we need to check that this
        #   is, indeed, the case by calling self.value_changed('fc') after we
        #   update the current value via self.set_current_value('fc', 12007).
        if self.value_changed('fc'):
            # Yup! The value has changed even after we coerced it to the nearest
            # calibrated frequency.
            self._token_valid = False
        else:
            # Despite the fact that self.set_fc was called as if the carrier
            # frequency has changed, we have coerced the value to the nearest
            # frequency and it turns out the carrier frequency we use for
            # computing the token has not changed.  Therefore, nothing needs to
            # be done.
            pass

    #########################################################################
    # Methods for computing/caching waveform
    #########################################################################

    def compute_waveform(self, calibration, hw_attenuation):
        # We could also cache the waveform as well since it will not change if
        # we are only roving level.
        waveform = self._get_token() * self._get_envelope()
        
        # Given the calibration file and hardware attenuation (which we do not
        # wish to change), compute the appropriate scaling factor for the
        # waveform.
        fc = self.get_current_value('fc')
        level = self.get_current_value('level')
        sf = calibration.get_sf(fc, level, hw_attenuation, voltage=1, gain=0)
        log.debug('Scaling factor is %f', sf)
        if sf > MAX_VRMS:
            self.dt_waveform_error = True
            mesg = 'Requested sound level too high for expected speaker ' \
                   'range. Signal will be distorted.  '
            self.notify(mesg)
        else:
            self.dt_waveform_error = False
        self.dt_waveform_sf = sf
        return sf*waveform

class Paradigm(
        PumpParadigmMixin,
        CLParadigmMixin,
        AbstractAversiveParadigm, 
        ):

    repeat_fa = False
    go_probability = 'h_uniform(c_safe, 3, 7)'

    kw = {'context': True, 'log': True}

    fc = Expression(2e3, label='Center frequency (Hz)', **kw)
    level = Expression(20, label='Level (dB SPL)', help='Test', **kw)
    rise_fall_time = Expression(0.0025, label='Rise/fall time (s)', **kw)

    # This is a list of lists.  Each entry in the list is a two-element list,
    # [frequency, max_spl].  We default to a single entry of 2 kHz with a max
    # level of 20.0 dB SPL.  By setting the minimum length of the list to 1, we
    # prevent the user from deleting the only entry in the list.  We need to use
    # CFloat here (this means accept any value that can be cast to float) since
    # the GUI widget will a string value (e.g. '80.0' rather than the actual
    # floating point value, 80.0).  By indicating that this is a list of CFloat,
    # the string value will automatically be converted to the correct type, a
    # floating-point value.
    expected_speaker_range = List(List(CFloat), [[2e3, 20.0]], minlen=1, context=True,
            log=False)

    dt_group = VGroup(
            VGroup(
                'rise_fall_time',
                'fc',
                'level',
                label='Signal',
                show_border=True,
                ),
            VGroup(
                # Let's help the user out a little with a label to remind them
                # how to add/remove values from the editor, especially since I
                # removed all the buttons that they used to have.  This uses the
                # implicit string concatenation that the Python interpreter
                # uses.  Specifically, x = 'string a' ' ' 'string b' is
                # equivalent to x = 'string a string b'. 
                Label('Select widget then hit Insert to add item '
                      'and Delete to remove item'),
                Item('expected_speaker_range', 
                     editor=TabularEditor(
                         adapter=TabularAdapter(
                            columns=['Freq. (Hz)', 'Max level (dB SPL)'], 
                            default_value=[1000.0, -20.0]
                            )
                         ),
                     show_label=False),
                label='Expected range of tones',
                show_border=True,
                ),
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
                'speaker',
                Include('dt_group'),
                label='Signal',
                ),
            )

class Data(AversiveData, AversiveCLDataMixin, PumpDataMixin):
    pass

class Experiment(AbstractAversiveExperiment, CLExperimentMixin):

    data = Instance(Data, ())
    paradigm = Instance(Paradigm, ())

node_name = 'AversiveDTExperiment'

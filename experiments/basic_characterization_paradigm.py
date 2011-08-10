from abstract_experiment_paradigm import AbstractExperimentParadigm
from enthought.traits.api import Range, Bool, Button, Any
from enthought.traits.ui.api import View, VGroup, HGroup, Item

class BasicCharacterizationParadigm(AbstractExperimentParadigm):
    
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

    primary_attenuation     = Range(0, 120, 120, init=True, immediate=True)
    secondary_attenuation   = Range(0, 120, 120, init=True, immediate=True)

    token_duration          = Range(0.01, 10.0, 1.0, init=True, immediate=True)
    trial_duration          = Range(0.01, 20.0, 2.0, init=True, immediate=True)
    center_frequency        = Range(100, 50e3, 5e3, init=True, immediate=True)
    bandwidth_ratio         = Range(0.0, 2, 0.3, init=True, immediate=True)
    modulation_frequency    = Range(0.0, 100, 5.0, init=True, immediate=True)
    modulation_depth        = Range(0.0, 1.0, 0.0, init=True, immediate=True)

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
                'center_frequency',
                'bandwidth_ratio',
                'modulation_frequency',
                'modulation_depth'
                ),
            width=400,
            title='Positive paradigm editor',
            )

if __name__ == '__main__':
    BasicCharacterizationParadigm().configure_traits()

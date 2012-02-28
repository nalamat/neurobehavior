from traits.api import HasTraits, Bool, List, Instance, Float, Button
from traitsui.api import TabularEditor
from traitsui.tabular_adapter import TabularAdapter

class SpeakerRange(HasTraits):
    
    frequency = Float(store='attribute', context=True, log=False)
    max_level = Float(store='attribute', context=True, log=False)
    
    def __lt__(self, other):
        if not isinstance(other, SpeakerRange):
            return NotImplemented
        a = self.frequency, self.max_level
        b = other.frequency, other.max_level
        return a < b
    
    def __eq__(self, other):
        if not isinstance(other, SpeakerRange):
            return NotImplemented
        a = self.frequency, self.max_level
        b = other.frequency, other.max_level
        return a == b

speaker_range_columns = [
    ('Frequency (Hz)', 'frequency'),
    ('Max level (dB SPL)', 'max_level'), ]

speaker_range_editor = TabularEditor(
    auto_update=True,
    editable=True,
    multi_select=True,
    selected='_selected_speaker_range',
    adapter=TabularAdapter(columns=speaker_range_columns),
    )

class FixedAttenuationParadigmMixin(HasTraits):

    # Settings for ensuring speaker attenuation does not change during
    # experiment
    fixed_attenuation = Bool(False, label='Fixed attenuation?',
            context=True, log=True)
    expected_speaker_range = List(Instance(SpeakerRange), container=True,
            store='attribute', label='Expected speaker range', context=True)

    # Buttons to allow modifying the speaker range
    _add_speaker_range = Button('Add')
    _remove_speaker_range = Button('Remove')
    _sort_speaker_range = Button('Sort')
    _selected_speaker_range = List(transient=True)
    
    def __sort_speaker_range_fired(self):
        self.expected_speaker_range.sort()
    
    def __add_speaker_range_fired(self):
        # If a setting is selected, let's assume that the user wishes to
        # duplicate 
        if len(self._selected_speaker_range) != 0:
            for speaker_range in self._selected_speaker_range:
                self.expected_speaker_range.append(speaker_range.clone_traits())
        else:
            self.expected_speaker_range.append(SpeakerRange())
        
    def __remove_speaker_range_fired(self):
        for speaker_range in self._selected_speaker_range:
            self.expected_speaker_range.remove(speaker_range)
        self._selected_speaker_range = []


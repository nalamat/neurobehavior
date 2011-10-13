from enthought.traits.api import HasTraits, Float, Bool, Button, Instance, List, Str
from enthought.traits.ui.api import VGroup, View, Item, HGroup
from evaluate import Expression

from enthought.traits.ui.api import TabularEditor
from enthought.traits.ui.tabular_adapter import TabularAdapter

class TrackSetting(HasTraits):
    setting = Str(context=True, log=False)
    
track_setting_editor = TabularEditor(
    auto_update=True,
    editable=True,
    multi_select=True,
    selected='_selected_tracks',
    adapter=TabularAdapter(width=100, columns=[('Track Setting', 'setting')]),
    )

class MaximumLikelihoodParadigmMixin(HasTraits):
    
    add = Button()
    remove = Button()
    _selected_tracks = List(Instance(TrackSetting))
    
    def _add_fired(self):
        # If a setting is selected, let's assume that the user wishes to
        # duplicate 
        if len(self._selected_tracks) != 0:
            for setting in self._selected_tracks:
                new = TrackSetting()
                new.copy_traits(setting)
                self.tracks.append(new)
        else:
            self.tracks.append(TrackSetting())
        
    def _remove_fired(self):
        for setting in self._selected_tracks:
            self.tracks.remove(setting)
    
    tracks = List(Instance(TrackSetting), editor=track_setting_editor,
                  container=True, context=True, log=False)
    
    go_probability = Expression('0.5 if c_nogo < 5 else 1', context=True,
            store='attribute', label='GO probability')
    
    initial_setting = Float(40, label='Initial setting', store='attribute')
    remind_setting = Float(-20, label='Remind setting', context=True,
                           store='attribute')
    nogo_setting = Float(-20, label='Nogo setting', context=True,
                         store='attribute')
    repeat_fa = Bool(True, label='Repeat nogo if FA?', context=True,
                     store='attribute')
    
    # Parameters required for seeding the maximum likelihood estimator
    fa_rate = Expression('arange(0, 1.0, .1)', label=u'\u03B1 (FA rate)',
            context=True, log=False)
    midpoint = Expression('arange(1, 100, 1)', label='m (midpoint)',
            context=True, log=False)
    slope = Expression('arange(0.1, 1, 0.1)', label=u'k (slope)', context=True,
            log=False)
    
    maximum_likelihood_paradigm_mixin_group = VGroup(
        HGroup('add', 'remove', show_labels=False),
        Item('tracks', show_label=False),
        VGroup(
            Item('initial_setting', enabled_when='not finalized'),
            Item('remind_setting'),
            Item('nogo_setting'),
            Item('repeat_fa'),
            Item('go_probability'),
            label='Track settings',
            show_border=True,
            ),
        VGroup(
            Item('fa_rate', enabled_when='not finalized'),
            Item('midpoint', enabled_when='not finalized'),
            Item('slope', enabled_when='not finalized'),
            label='Parameter range',
            show_border=True,
            ),
        label='ML settings',
        )
    
    traits_view = View(maximum_likelihood_paradigm_mixin_group)    
    
if __name__ == '__main__':
    MaximumLikelihoodParadigmMixin().configure_traits()

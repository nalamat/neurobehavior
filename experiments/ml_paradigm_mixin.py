from enthought.traits.api import HasTraits, Float, Bool, List, Str
from traitsui.api import VGroup, View, Item, ListStrEditor
from .evaluate import Expression

class MLParadigmMixin(HasTraits):
    
    kw = {'context': True, 'log': True}

    tracks = List(['sweetpoint'], Str, minlen=1, context=True, log=False)

    go_probability = Expression('0.5 if c_nogo < 5 else 1', 
                                label='GO probability', **kw)
    initial_setting = Float(40, label='Initial setting', **kw)
    remind_setting = Float(-20, label='Remind setting', **kw)
    nogo_setting = Float(-20, label='Nogo setting', **kw)
    repeat_fa = Bool(True, label='Repeat nogo if FA?', **kw)
    
    # Parameters required for seeding the maximum likelihood estimator.  Note
    # that positive_data.PositiveData defines a context variable called fa_rate.
    # Hence, we need to prepend fa_rate here with "ml_" to avoid confusion
    # between the two.
    ml_fa_rate = Expression('arange(0, 1.0, .1)', label=u'\u03B1 (FA rate)')
    ml_midpoint = Expression('arange(1, 100, 1)', label='m (midpoint)')
    ml_slope = Expression('arange(0.1, 1, 0.1)', label=u'k (slope)')
    _finalized = Bool(False)
    
    maximum_likelihood_paradigm_mixin_group = VGroup(
        Item('tracks', show_label=False, editor=ListStrEditor(title='Track')),
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
            # We do not allow the user to change the guess during the
            # experiment.  It's just too complicated to handle the logic at the
            # moment.  It is doable if someone's motivated enough to write the
            # code ...
            Item('ml_fa_rate', enabled_when='not _finalized'),
            Item('ml_midpoint', enabled_when='not _finalized'),
            Item('ml_slope', enabled_when='not _finalized'),
            label='Parameter space to explore',
            show_border=True,
            ),
        label='ML settings',
        )
    
    traits_view = View(maximum_likelihood_paradigm_mixin_group)    
    
if __name__ == '__main__':
    ml = MLParadigmMixin()
    ml.ml_midpoint = '4+5'
    #ml.configure_traits()
    #print ml.ml_fa_rate
    print ml.ml_fa_rate.evaluate()
    print ml.ml_midpoint.evaluate()

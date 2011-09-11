from enthought.traits.api import Trait, Instance, Range, Float, Property, \
        Bool, List, Int, Str, Tuple, Button
from enthought.traits.ui.api import VGroup, Item, HGroup, View, Include, \
        Tabbed

from cns import choice

from abstract_experiment_paradigm import AbstractExperimentParadigm

from evaluate import Expression

class AbstractAversiveParadigm(AbstractExperimentParadigm):
    '''
    Defines an aversive paradigm, but not the signals that will be used.  This
    allows us to use either a generic circuit with two buffers for the warn/safe
    signal, or a circuit that is specialized for a specific kind of signal (e.g.
    FM).
    '''

    kw = {'context': True, 'store': 'attribute', 'log': True}

    prevent_disarm = Bool(True, label='Prevent disarm of aversive?', **kw)

    # By default, Range provides a slider as the GUI widget.  Note that you can
    # override the default widget if desired.
    lick_th = Expression(0.75, label='Contact threshold', **kw)
    aversive_delay = Expression(1, label='Aversive delay (s)', **kw)
    aversive_duration = Expression(0.3, label='Aversive duration (s)', **kw)
    trial_duration = Expression(1.0, label='Trial duration (s)', **kw) 

    shock_level = Range(0.0, 5.0, 0.5, label='Shock level (mA)', immediate=True,
            store='attribute', context=True)

    _set_shock_a = Button('Level A')
    _set_shock_b = Button('Level B')
    _set_shock_c = Button('Level C')
    _set_shock_off = Button('Off')

    shock_a = Float(2.75, store='attribute')
    shock_b = Float(1.6, store='attribute')
    shock_c = Float(0.5, store='attribute')

    def __set_shock_a_fired(self):
        self.shock_level = self.shock_a

    def __set_shock_b_fired(self):
        self.shock_level = self.shock_b

    def __set_shock_c_fired(self):
        self.shock_level = self.shock_c

    def __set_shock_off_fired(self):
        self.shock_level = 0
    
    #===========================================================================
    # The views available
    #===========================================================================

    timing_group = VGroup(
            'prevent_disarm',
            'trial_duration',
            'aversive_delay',
            'aversive_duration',
            'lick_th',
            show_border=True, 
            label='Trial settings',
            )

    shock_group = VGroup(
        HGroup(
            VGroup('_set_shock_a', 'shock_a', show_labels=False),
            VGroup('_set_shock_b', 'shock_b', show_labels=False),
            VGroup('_set_shock_c', 'shock_c', show_labels=False),
            VGroup('_set_shock_off', show_labels=False),
            ),
        'shock_level',
        show_border=True,
        label='Shock settings'
        )

    abstract_aversive_paradigm_group = VGroup(
            Include('timing_group'), 
            Include('shock_group'),
            show_labels=False,
            show_border=True,
            label='Paradigm',
            )

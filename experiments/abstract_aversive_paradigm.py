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
    # Trait defines a drop-down selector if you provide it with a list of
    # options
    prevent_disarm = Bool(True, store='attribute', context=True,
            label='Prevent disarming of aversive stimulus?')

    # By default, Range provides a slider as the GUI widget.  Note that you can
    # override the default widget if desired.
    lick_th = Expression(0.75, label='Contact threshold')
    aversive_delay = Expression(1, label='Aversive Stimulus Delay (s)')
    aversive_duration = Expression(0.3, label='Aversive Stimulus Duration (s)')
    trial_duration = Expression(1.0, label='Trial duration (s)') 

    shock_level = Range(0.0, 5.0, 0.5, label='Shock level (mA)', immediate=True,
            store='attribute')

    _set_shock_a = Button('Level A', ignore=True)
    _set_shock_b = Button('Level B', ignore=True)
    _set_shock_c = Button('Level C',ignore=True)
    _set_shock_off = Button('Off', ignore=True)

    shock_a = Float(2.75, ignore=True, store='attribute')
    shock_b = Float(1.6, ignore=True, store='attribute')
    shock_c = Float(0.5, ignore=True, store='attribute')

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
    par_group = VGroup(
            # Use the attribute called 'par_remind' and give it a label of
            # 'Remind Parameter' in the GUI.  Create the appropriate widget for
            # the "type" of the attribute.  
            Item('remind', style='custom', label='Remind'),
            Item('safe', style='custom', label='Safe'),
            VGroup(
                Item('order', label='Order'),
                HGroup(Item('warn_sequence', show_label=False)),
                show_border=True, 
                label='Warn'
                ),
            show_border=True, 
            label='Signal Parameters')

    trial_group = VGroup(
            Item('num_safe', label='Number of safe trials'),
            Item('trial_duration', label='Trial duration (s)'),
            )

    timing_group = VGroup(
            trial_group, 
            'prevent_disarm',
            'aversive_delay',
            'aversive_duration',
            'shock_level',
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
        )

    traits_view = View(
            Include('shock_group'),
            Tabbed(
                Include('par_group'), 
                Include('timing_group'), 
                Include('signal_group'),
                ),
            resizable=True,
            title='Aversive Paradigm editor')

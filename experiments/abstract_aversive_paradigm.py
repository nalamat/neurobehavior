from enthought.traits.api import Trait, Instance, Range, Float, Property, \
        Bool, List, Int, Str, Tuple
from enthought.traits.ui.api import VGroup, Item, HGroup, View, Include, \
        Tabbed

from cns import choice

from abstract_experiment_paradigm import AbstractExperimentParadigm
from pump_paradigm_mixin import PumpParadigmMixin

from evaluate import Expression

class AbstractAversiveParadigm(AbstractExperimentParadigm, PumpParadigmMixin):
    '''Defines an aversive paradigm, but not the signals that will be used.
    This allows us to use either a generic circuit with two buffers for the
    warn/safe signal, or a circuit that is specialized for a specific kind of
    signal (e.g. FM).
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
    shock_level = Expression(0.5, label='Shock level (mA)')

    num_safe = Expression('randint(2, 5)', label='Number of safes')
    trial_duration = Expression(1.0, label='Trial duration (s)') 

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

    traits_view = View(
            Tabbed(
                Include('par_group'), 
                Include('timing_group'), 
                Include('signal_group'),
                ),
            resizable=True,
            title='Aversive Paradigm editor')

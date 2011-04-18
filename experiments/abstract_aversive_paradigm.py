from enthought.traits.api import Trait, Instance, Range, Float, Property, \
        Bool, List, Int, Str, Tuple
from enthought.traits.ui.api import VGroup, Item, HGroup, View, Include, \
        Tabbed

from cns import choice

from trial_setting import TrialSetting, trial_setting_editor
from abstract_experiment_paradigm import AbstractExperimentParadigm
from pump_paradigm_mixin import PumpParadigmMixin

from eval import ExpressionTrait

class AbstractAversiveParadigm(AbstractExperimentParadigm, PumpParadigmMixin):
    '''Defines an aversive paradigm, but not the signals that will be used.
    This allows us to use either a generic circuit with two buffers for the
    warn/safe signal, or a circuit that is specialized for a specific kind of
    signal (e.g. FM).
    '''
    # Trait defines a drop-down selector if you provide it with a list of
    # options
    order         = Trait('descending', choice.options, store='attribute',
                          init=True)
    warn_sequence = List(Instance(TrialSetting), minlen=1,
                         store='child', init=True, editor=trial_setting_editor)
    remind        = Instance(TrialSetting, (), store='child', init=True)
    safe          = Instance(TrialSetting, (), store='child', init=True)

    def _warn_sequence_default(self):
        return [TrialSetting()]

    prevent_disarm = Bool(True, store='attribute', init=True)

    # By default, Range provides a slider as the GUI widget.  Note that you can
    # override the default widget if desired.
    lick_th = Range(0.0, 1.0, 0.75, store='attribute')
    aversive_delay = ExpressionTrait(1)
    aversive_duration = ExpressionTrait(0.3)

    num_safe = ExpressionTrait('randint(2, 5)')
    trial_duration = ExpressionTrait(1.0)

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
            Item('prevent_disarm',
                 label='Prevent disarming of stimulus?'),
            Item('aversive_delay', 
                 label='Aversive stimulus delay (s)'),
            Item('aversive_duration',
                 label='Aversive stimulus duration (s)'),
            Item('lick_th', label='Contact threshold'),
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

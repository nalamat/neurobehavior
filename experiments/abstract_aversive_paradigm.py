from enthought.traits.api import Trait, Instance, Range, Float, Property, \
        Bool, List, Int, Str, Tuple
from enthought.traits.ui.api import VGroup, Item, HGroup, View, Include, \
        Tabbed

from cns import choice

from trial_setting import TrialShockSetting, table_editor
from abstract_experiment_paradigm import AbstractExperimentParadigm
from pump_paradigm_mixin import PumpParadigmMixin

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
    warn_sequence = List(Instance(TrialShockSetting), minlen=1,
                         store='child', init=True)
    remind        = Instance(TrialShockSetting, (), store='child', init=True)
    safe          = Instance(TrialShockSetting, (), store='child', init=True)

    def _warn_sequence_default(self):
        return [TrialShockSetting()]

    prevent_disarm = Bool(True, store='attribute', init=True)

    # By default, Range provides a slider as the GUI widget.  Note that you can
    # override the default widget if desired.
    lick_th = Range(0.0, 1.0, 0.75, store='attribute', init=True)
    aversive_delay = Float(1, store='attribute', init=True)
    aversive_duration = Float(0.3, store='attribute', init=True)

    min_safe = Int(2, store='attribute', init=True)
    max_safe = Int(4, store='attribute', init=True)
    trial_duration = Float(1.0, store='attribute', init=True)

    #===========================================================================
    # Error checks
    #===========================================================================
    err_num_trials = Property(Bool, depends_on='min_safe, max_safe', error=True)
    mesg_num_trials = 'Max trials must be >= min trials'

    def _get_err_num_trials(self):
        return self.min_safe > self.max_safe

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
                HGroup(
                    Item('warn_sequence', show_label=False, editor=table_editor)
                    ),
                show_border=True, 
                label='Warn'
                ),
            show_border=True, 
            label='Signal Parameters')

    trial_group = VGroup(
            Item('min_safe', label='Minimum safe trials',
                 invalid='err_num_trials'),
            Item('max_safe', label='Maximum safe trials',
                 invalid='err_num_trials'),
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
                par_group, 
                timing_group, 
                Include('signal_group'),
                ),
            resizable=True,
            title='Aversive Paradigm editor')

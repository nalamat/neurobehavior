from abstract_experiment_paradigm import AbstractExperimentParadigm

from cns import choice
from enthought.traits.api import Instance, Float, DelegatesTo, Int, Float, \
        CBool, Enum, List, Tuple, HasTraits, Trait, on_trait_change, Range, \
        Property
from enthought.traits.ui.api import View, spring, VGroup, Item, \
    InstanceEditor, Include, EnumEditor, Tabbed
from cns.traits.ui.api import ListAsStringEditor

from pump_paradigm_mixin import PumpParadigmMixin

from enthought.traits.ui.table_column import ObjectColumn
from enthought.traits.ui.api import TableEditor, TextEditor

from trial_setting import TrialSetting, trial_setting_editor

from eval import ExpressionTrait

class AbstractPositiveParadigm(AbstractExperimentParadigm, PumpParadigmMixin):

    parameters  = List(Instance(TrialSetting), [], store='child')
    nogo        = Instance(TrialSetting, (), store='child')
    remind      = Instance(TrialSetting, (), store='child')

    def _parameters_default(self):
        return [TrialSetting()]

    parameter_order = Trait('shuffled set', choice.options, store='attribute',
                            init=True, label='Parameter order')
    pump_rate       = ExpressionTrait(1.5, label='Pump rate (ml/min)')
    reward_volume   = ExpressionTrait(25, label='Reward volume (ul)')

    num_nogo = ExpressionTrait('int(clip(exponential(2), 0, 5))', label='NOGO number')

    # Needs to be CBool because Pytables returns numpy.bool_ type which gets
    # rejected by Bool trait
    repeat_FA = CBool(store='attribute', init=True, label='Repeat NOGO if FA')

    signal_offset_delay = ExpressionTrait(0.5, label='Signal offset delay (s)')
    intertrial_duration = ExpressionTrait(0.1, label='Intertrial duration (s)')
    reaction_window_delay = ExpressionTrait(0, label='Withdraw delay (s)')
    reaction_window_duration = ExpressionTrait(1.5, label='Withdraw duration (s)')

    response_window_duration = ExpressionTrait(3, label='Response duration (s)')

    timeout_trigger  = Enum('FA only', 'Anytime', label='Timeout Mode')
    timeout_duration = ExpressionTrait(15, label='TO duration (s)')
    timeout_grace_period = ExpressionTrait(2.5, label='Timeout grace period (s)')
    fa_puff_duration = ExpressionTrait(0.0, label='FA puff duration (s)')

    poke_duration = ExpressionTrait('uniform(0.1, 0.2)', label='Poke duration (s)')

    parameter_view = VGroup(
            Item('nogo', style='custom'),
            Item('remind', style='custom'),
            VGroup(Item('parameter_order', label='Order')),
            Item('parameters', editor=trial_setting_editor,
                 show_label=False),
            label='Trial Sequence',
            show_border=True,
            )

    traits_view = View(
            Tabbed(
                Include('parameter_view'),
                Include('signal_group'),
                VGroup(
                    'signal_offset_delay',
                    'intertrial_duration',
                    'reaction_window_delay',
                    'reaction_window_duration',
                    'response_window_duration',
                    'timeout_trigger',
                    'timeout_duration',
                    'fa_puff_duration',
                    'poke_duration',
                    'pump_rate',
                    'reward_volume',
                    Item('num_nogo', label='NOGO'),
                    Item('repeat_FA', label='Add a NOGO if false alarm?'),
                    label='Settings',
                    ),
                ),
            resizable=True,
            title='Positive paradigm editor',
            width=100,
            )

if __name__ == '__main__':
    AbstractPositiveParadigm().configure_traits()

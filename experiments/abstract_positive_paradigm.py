from abstract_experiment_paradigm import AbstractExperimentParadigm

from cns import choice
from enthought.traits.api import Instance, Float, DelegatesTo, Int, Float, \
        CBool, Enum, List, Tuple, HasTraits, Trait, on_trait_change, Range, \
        Property
from enthought.traits.ui.api import View, spring, VGroup, Item, \
    InstanceEditor, Include, EnumEditor, Tabbed
from cns.traits.ui.api import ListAsStringEditor

from pump_paradigm_mixin import PumpParadigmMixin
from signals import signal_options

from enthought.traits.ui.table_column import ObjectColumn
from enthought.traits.ui.api import TableEditor, TextEditor

from trial_setting import TrialSetting, trial_setting_editor

from eval import ExpressionTrait

class AbstractPositiveParadigm(AbstractExperimentParadigm, PumpParadigmMixin):

    parameters = List(Instance(TrialSetting), [], store='child', init=True)

    def _parameters_default(self):
        return [TrialSetting()]

    parameter_order = Trait('shuffled set', choice.options, store='attribute',
                            init=True)
    nogo_parameter  = Float(store='attribute', init=True)

    reward_duration = ExpressionTrait(1.0, store='attribute', ignore=True)
    reward_duration = ExpressionTrait(1.0, store='attribute', ignore=True)
    pump_rate       = ExpressionTrait(1.5, store='attribute', init=True)
    reward_volume   = ExpressionTrait(25, store='attribute', init=True)
    reward_volume   = Float(25, store='attribute', init=True, 
                            label=u'Reward volume (ul)')

    def _reward_duration_changed(self, value):
        # ul = ml/m * (s/60) * 1000 ul/ml
        self.reward_volume = self.pump_rate * (value/60.0) * 1e3

    def _reward_volume_changed(self, value):
        # s = (1e-3 ml/ul / (ml/m)) * 60 s/m
        self.reward_duration = value*1e-3/self.pump_rate*60

    def _pump_rate_changed(self, value):
        # ul = ml/m * (m/60s) * 1000 ul/ml
        # s = ul / (ml/m * 1000 ul/ml) * 60s/m
        #self.reward_volume = value * (self.reward_duration/60.0) * 1e3
        self.reward_duration = self.reward_volume / (value*1e3) * 60.0

    nogo = ExpressionTrait('randint(2, 5)')

    # Needs to be CBool because Pytables returns numpy.bool_ type which gets
    # rejected by Bool trait
    repeat_FA = CBool(store='attribute', init=True)

    signal_offset_delay = ExpressionTrait(0.5, store='attribute', init=True)
    intertrial_duration = ExpressionTrait(0.5, store='attribute', init=True)
    reaction_window_delay = ExpressionTrait(0, store='attribute', init=True)
    reaction_window_duration = ExpressionTrait(1.5, store='attribute', init=True)


    response_window_duration = ExpressionTrait(3, store='attribute', init=True)

    timeout_trigger  = Enum('FA only', 'Anytime', store='attribute', init=True)
    timeout_duration = ExpressionTrait(5, store='attribute', init=True)
    timeout_grace_period = ExpressionTrait(2.5, store='attribute', init=True)
    fa_puff_duration = Float(0.2, store='attribute', init=True, 
                             label='FA puff duration (s)')

    poke_duration = ExpressionTrait('uniform(0.1, 0.5)', store='attribute',
            init=True)

    parameter_view = VGroup(
            Item('nogo_parameter'),
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
                    Item('nogo', label='NOGO'),
                    Item('repeat_FA', label='Add a NOGO if false alarm?'),
                    label='Trial',
                    ),
                VGroup(
                    Item('signal_offset_delay',
                         label='Signal offset delay (s)'),
                    Item('intertrial_duration',
                         label='Minimum intertrial duration (s)'),
                    Item('reaction_window_delay',
                         label='Reaction window delay (s)'),
                    Item('reaction_window_duration',
                         label='Reaction window (s)'),
                    Item('response_window_duration',
                         label='Response window (s)'),
                    Item('timeout_trigger',
                         label='TO mode'),
                    Item('timeout_duration',
                         label='TO minimum duration (s)'),
                    'fa_puff_duration',
                    #Item('timeout_grace_period', 
                    Item('poke_duration', label='Poke duration (s)'),
                    label='Timing',
                    ),
                VGroup(
                    'pump_rate',
                    'reward_volume',
                    Item('reward_duration', style='readonly'),
                    label='Reward',
                    ),
                ),
            resizable=True,
            title='Positive paradigm editor',
            width=100,
            )

if __name__ == '__main__':
    AbstractPositiveParadigm().configure_traits()

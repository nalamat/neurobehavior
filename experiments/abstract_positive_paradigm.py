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

class TrialSetting(HasTraits):

    parameter       = Float(1.0, store='attribute')

    def __cmp__(self, other):
        return cmp(self.parameter, other.parameter)

    def __str__(self):
        return "{0}".format(self.parameter)

table_editor = TableEditor(
        editable=True,
        deletable=True,
        show_toolbar=True,
        row_factory=TrialSetting,
        columns=[
            ObjectColumn(name='parameter', label='Parameter', width=75),
            ]
        )

class AbstractPositiveParadigm(AbstractExperimentParadigm, PumpParadigmMixin):

    parameters = List(Instance(TrialSetting), [], store='child', init=True)

    def _parameters_default(self):
        return [TrialSetting()]

    parameter_order = Trait('shuffled set', choice.options, store='attribute',
                            init=True)
    nogo_parameter  = Float(store='attribute')
    reward_duration = Float(1.0, store='attribute', init=True)
    pump_rate = Float(1.0, store='attribute', init=True)
    reward_volume = Property(Float, depends_on='reward_duration, pump_rate',
                             store='attribute')

    def _get_reward_volume(self):
        # Rate is in ml/min, compute mls dispensed then return as ul
        return 1e3 * self.pump_rate * self.reward_duration/60.0

    min_nogo = Int(0, store='attribute', init=True)
    max_nogo = Int(0, store='attribute', init=True)

    # Needs to be CBool because Pytables returns numpy.bool_ type which gets
    # rejected by Bool trait
    repeat_FA = CBool(store='attribute', init=True)

    signal_offset_delay = Float(0.5, store='attribute', init=True)
    intertrial_duration = Float(0.5, store='attribute', init=True)
    reaction_window_delay = Float(0, store='attribute', init=True)
    reaction_window_duration = Float(1.5, store='attribute', init=True)

    response_window_duration = Float(3, store='attribute', init=True)
    reward_duration = Float(0.5, store='attribute', init=True)

    timeout_trigger  = Enum('FA only', 'Anytime', store='attribute', init=True)
    timeout_duration = Float(5, store='attribute', init=True)
    timeout_grace_period = Float(2.5, store='attribute', init=True)

    poke_duration_lb = Float(0.1, store='attribute', init=True)
    poke_duration_ub = Float(0.5, store='attribute', init=True)

    parameter_view = VGroup(
            Item('nogo_parameter'),
            VGroup(Item('parameter_order', label='Order')),
            Item('parameters', editor=table_editor,
                 show_label=False),
            label='Trial Sequence',
            show_border=True,
            )

    traits_view = View(
            Tabbed(
                Include('parameter_view'),
                Include('signal_group'),
                VGroup(
                    Item('min_nogo', label='Minimum NOGO'),
                    Item('max_nogo', label='Maximum NOGO'),
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
                    Item('timeout_grace_period', 
                         label='TO grace period (s)'),
                    Item('poke_duration_lb', label='Min poke duration (s)'),
                    Item('poke_duration_ub', label='Max poke duration (s)'),
                    label='Timing',
                    ),
                VGroup(
                    Item('reward_duration', label='Reward duration (s)'),
                    Item('pump_rate', label='Pump rate (mL/m)'),
                    Item('reward_volume', label='Reward volume (ul)',
                         style='readonly'),
                    label='Reward',
                    ),
                ),
            resizable=False,
            title='Positive paradigm editor',
            width=100,
            )

if __name__ == '__main__':
    PositiveParadigm().configure_traits()

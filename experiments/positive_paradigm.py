from abstract_experiment_paradigm import AbstractExperimentParadigm

from cns import choice
from enthought.traits.api import Instance, Float, DelegatesTo, Int, Float, \
        CBool, Enum, List, Tuple, HasTraits, Trait, on_trait_change, Range
from enthought.traits.ui.api import View, spring, VGroup, Item, \
    InstanceEditor, Include, EnumEditor, Tabbed
from cns.traits.ui.api import ListAsStringEditor

from pump_paradigm_mixin import PumpParadigmMixin
from signals import signal_options

from enthought.traits.ui.table_column import ObjectColumn
from enthought.traits.ui.api import TableEditor, TextEditor

class TrialSetting(HasTraits):

    parameter       = Float(1.0, store='attribute')
    reward_duration = Float(0.5, store='attribute')
    reward_rate     = Float(0.3, store='attribute')

    def _anytrait_changed(self, name, new):
        print "CHANGE", name, new

    def __cmp__(self, other):
        return cmp(self.parameter, other.parameter)

    def __str__(self):
        return "{0}, {1}s at {2}mL/min".format(self.parameter,
                self.reward_duration, self.reward_rate)

table_editor = TableEditor(
        editable=True,
        deletable=True,
        show_toolbar=True,
        row_factory=TrialSetting,
        columns=[
            ObjectColumn(name='parameter', label='Parameter', width=75),
            ObjectColumn(name='reward_duration', label='Reward duration',
                width=75),
            ObjectColumn(name='reward_rate', label='Reward rate', width=75),
            ]
        )

class PositiveParadigm(AbstractExperimentParadigm, PumpParadigmMixin):

    parameters = List(Instance(TrialSetting), [], store='child')

    signal = Enum(signal_options.keys())
    signal_group = VGroup(
            Item('signal', editor=EnumEditor(values=signal_options)),
            Item('signal', editor=InstanceEditor(), style='custom'),
            show_labels=False, show_border=True, label='Signal',
            )

    attenuation = Range(0, 120, 30, store='attribute')

    def _parameters_default(self):
        return [TrialSetting()]

    parameter_order = Trait('shuffled set', choice.options, store='attribute')
    nogo_parameter  = Float(store='attribute')

    min_nogo = Int(0, label='Minimum NOGO', store='attribute')
    max_nogo = Int(0, label='Maximum NOGO', store='attribute')

    trial_duration = Float(1, unit='s', store='attribute')

    # Needs to be CBool because Pytables returns numpy.bool_ type which gets
    # rejected by Bool trait
    repeat_FA = CBool(label='Repeat NOGO if FA?', store='attribute')

    signal_offset_delay = Float(0.5, unit='s', store='attribute')
    intertrial_duration = Float(0.5, unit='s', store='attribute')
    reaction_window_delay = Float(0, unit='s', store='attribute')
    reaction_window_duration = Float(1.5, unit='s', store='attribute')

    response_window_duration = Float(3, unit='s', store='attribute')
    reward_duration = Float(0.5, unit='s', store='attribute')

    timeout_trigger  = Enum('FA only', 'Anytime', store='attribute')
    timeout_duration = Float(5, unit='s', store='attribute')
    timeout_grace_period = Float(2.5, unit='s', store='attribute')

    poke_duration_lb = Float(0.1, unit='s', store='attribute')
    poke_duration_ub = Float(0.5, unit='s', store='attribute')

    traits_view = View(
            VGroup(
                VGroup(
                    Item('nogo_parameter'),
                    VGroup(Item('parameter_order', label='Order')),
                    Item('parameters', editor=table_editor,
                         show_label=False),
                    label='Trial Sequence',
                    show_border=True,
                    ),
                Tabbed(
                    VGroup(
                        Item('attenuation'),
                        Item('trial_duration'),
                        Item('signal', label='Signal types',
                             editor=EnumEditor(values=signal_options)),
                        Item('signal', editor=InstanceEditor(), style='custom',
                             show_label=False),
                        show_border=True, 
                        label='Signal',
                        ),
                    VGroup(
                        Item('nogo_parameter', label='NOGO parameter'),
                        'min_nogo',
                        'max_nogo',
                        'repeat_FA',
                        'signal_offset_delay',
                        'intertrial_duration',
                        'reaction_window_delay',
                        'reaction_window_duration',
                        'response_window_duration',
                        'timeout_trigger',
                        'timeout_duration',
                        'timeout_safe_period',
                        'poke_duration_lb',
                        'poke_duration_ub',
                        label='Trial Settings',
                        show_border=True,
                        ),
                    ),
                ),
            resizable=False,
            title='Positive paradigm editor',
            width=100,
            )

if __name__ == '__main__':
    PositiveParadigm().configure_traits()

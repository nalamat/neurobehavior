from enthought.traits.api import Float, Range, List, Instance, HasTraits
from enthought.traits.ui.api import *

from abstract_positive_paradigm import AbstractPositiveParadigm

class TrialSetting(HasTraits):

    parameter       = Float(1.0, store='attribute')
    #attenuation     = Range(0.0, 120.0, 30.0, store='attribute')
    attenuation     = Float(30.0, store='attribute')
    reward_duration = Float(0.5, store='attribute')
    reward_rate     = Float(0.3, store='attribute')

    def __cmp__(self, other):
        return cmp(self.parameter, other.parameter)

    def __str__(self):
        mesg = "{parameter} {attenuation}, {duration}s at {rate}mL/min"
        return mesg.format(parameter=self.parameter,
                attenuation=self.attenuation, duration=self.reward_duration,
                rate=self.reward_rate)

table_editor = TableEditor(
        editable=True,
        deletable=True,
        show_toolbar=True,
        row_factory=TrialSetting,
        columns=[
            ObjectColumn(name='parameter', label='Parameter', width=75),
            ObjectColumn(name='attenuation', label='Attenuation', width=75),
            ObjectColumn(name='reward_duration', label='Reward duration',
                width=75),
            ObjectColumn(name='reward_rate', label='Reward rate', width=75),
            ]
        )

class PositiveDTParadigm(AbstractPositiveParadigm):

    parameters = List(Instance(TrialSetting), [], store='child')
    rise_fall_time = Float(0.0025, store='attribute')

    parameter_view = VGroup(
            Item('nogo_parameter'),
            VGroup(Item('parameter_order', label='Order')),
            Item('parameters', editor=table_editor,
                 show_label=False),
            label='Trial Sequence',
            show_border=True,
            )

    signal_group = VGroup(
            Item('rise_fall_time', label='Rise/fall time (s)'),
            )

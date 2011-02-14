from enthought.traits.api import Float, Range, List, Instance, HasTraits
from enthought.traits.ui.api import *

from abstract_positive_paradigm import AbstractPositiveParadigm

class TrialSetting(HasTraits):

    parameter       = Float(1.0, store='attribute')
    attenuation     = Float(30.0, store='attribute')

    def __cmp__(self, other):
        return cmp(self.parameter, other.parameter)

    def __str__(self):
        mesg = "{parameter} {attenuation} dB"
        return mesg.format(parameter=self.parameter,
                           attenuation=self.attenuation)

table_editor = TableEditor(
        editable=True,
        deletable=True,
        show_toolbar=True,
        row_factory=TrialSetting,
        columns=[
            ObjectColumn(name='parameter', label='Parameter', width=50),
            ObjectColumn(name='attenuation', label='Attenuation', width=50),
            ]
        )

class PositiveDTParadigm(AbstractPositiveParadigm):

    parameters = List(Instance(TrialSetting), [], store='child', init=True)
    rise_fall_time = Float(0.0025, store='attribute', init=True)

    def _parameters_default(self):
        return [TrialSetting(parameter=0.016, attenuation=80),
                TrialSetting(parameter=0.032, attenuation=80),
                TrialSetting(parameter=0.064, attenuation=80),
                TrialSetting(parameter=0.128, attenuation=80),
                TrialSetting(parameter=0.256, attenuation=80),
                TrialSetting(parameter=0.256, attenuation=90),
                TrialSetting(parameter=0.128, attenuation=90),
                TrialSetting(parameter=0.064, attenuation=90),
                TrialSetting(parameter=0.032, attenuation=90),
                TrialSetting(parameter=0.016, attenuation=90),]

    parameter_view = VGroup(
            VGroup(Item('parameter_order', label='Order')),
            Item('parameters', editor=table_editor,
                 show_label=False),
            label='Trial',
            show_border=True,
            )

    signal_group = VGroup(
            Item('rise_fall_time', label='Rise/fall time (s)'),
            label='Signal',
            )

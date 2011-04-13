from enthought.traits.api import Float, Range, List, Instance, HasTraits, Enum
from enthought.traits.ui.api import *

from abstract_positive_paradigm import AbstractPositiveParadigm

class TrialSetting(HasTraits):

    parameter           = Float(1.0, store='attribute')
    attenuation         = Float(30.0, store='attribute')

    def __cmp__(self, other):
        return cmp((self.parameter, self.attenuation), 
                   (other.parameter, other.attenuation))

    def __str__(self):
        mesg = "{parameter} s {attenuation} dB"
        return mesg.format(parameter=self.parameter,
                           attenuation=self.attenuation)

table_editor = TableEditor(
        editable=True,
        deletable=True,
        show_toolbar=True,
        row_factory=TrialSetting,
        columns=[
            ObjectColumn(name='parameter', label='Duration', width=50),
            ObjectColumn(name='attenuation', label='Attenuation', width=50),
            ]
        )

class PositiveDTParadigm(AbstractPositiveParadigm):

    parameters          = List(Instance(TrialSetting), [], store='child',
                               init=True)
    rise_fall_time      = Float(0.0025, store='attribute', init=True)
    fc                  = Float(15e3, store='attribute', init=True)
    bandwidth           = Float(5e3, store='attribute', init=True)
    attenuation         = Enum(0, 20, 40, 60, store='attribute', init=True)

    def _parameters_default(self):
        return [TrialSetting(parameter=4.0, attenuation=10),
                #TrialSetting(parameter=0.064, attenuation=10),
                #TrialSetting(parameter=0.256, attenuation=10),
                #TrialSetting(parameter=0.256, attenuation=30),
                #TrialSetting(parameter=0.064, attenuation=30),
                TrialSetting(parameter=4.0, attenuation=40),]

    parameter_view = VGroup(
            VGroup(Item('parameter_order', label='Order')),
            Item('parameters', editor=table_editor,
                 show_label=False),
            label='Trial',
            show_border=True,
            )

    signal_group = VGroup(
            Item('speaker_mode', label='Speaker'),
            Item('rise_fall_time', label='Rise/fall time (s)'),
            Item('fc', label='Center frequency (Hz)'),
            Item('bandwidth', label='Bandwidth (Hz)'),
            Item('attenuation', label='Attenuation'),
            label='Signal',
            )

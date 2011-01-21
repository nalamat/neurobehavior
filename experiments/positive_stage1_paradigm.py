from enthought.traits.api import DelegatesTo, Enum, Range
from enthought.traits.ui.api import View, VGroup, Item, EnumEditor, \
        InstanceEditor
from abstract_experiment_paradigm import AbstractExperimentParadigm
from pump_paradigm_mixin import PumpParadigmMixin
from signals import signal_options

class PositiveStage1Paradigm(AbstractExperimentParadigm, PumpParadigmMixin):

    attenuation = Range(0.0, 120.0, 40)
    signal = DelegatesTo('selector', store='child')
    signal = Enum(signal_options.keys())

    traits_view = View(
            VGroup(
                Item('attenuation', label='Attenuation (dB)', style='text'),
                Item('signal', editor=EnumEditor(values=signal_options)),
                Item('signal', editor=InstanceEditor(), style='custom'),
                show_border=True, label='Signal'
                ),
            )

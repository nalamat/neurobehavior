from enthought.traits.api import DelegatesTo, Enum
from enthought.traits.ui.api import View, VGroup, Item, EnumEditor, \
        InstanceEditor
from abstract_experiment_paradigm import AbstractExperimentParadigm
from pump_paradigm_mixin import PumpParadigmMixin
from signals import signal_options

class PositiveStage1Paradigm(AbstractExperimentParadigm, PumpParadigmMixin):

    signal = DelegatesTo('selector', store='child')
    signal = Enum(signal_options.keys())

    traits_view = View(
            VGroup(
                Item('signal', editor=EnumEditor(values=signal_options)),
                Item('signal', editor=InstanceEditor(), style='custom'),
                show_border=True, label='Signal'
                ),
            )

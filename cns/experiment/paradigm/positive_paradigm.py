from cns.experiment.paradigm.paradigm import Paradigm
from cns import choice
from cns.signal.type import Tone, Noise
from cns.signal.signal_dialog import SignalSelector
from enthought.traits.api import Instance, Float, DelegatesTo, Int, Float, \
        CBool, Enum, List, Tuple, HasTraits, Trait
from enthought.traits.ui.api import View, spring, VGroup, Item, \
    InstanceEditor, Include
from cns.traits.ui.api import ListAsStringEditor

from .pump_settings_mixin import PumpSettingsMixin

class PositiveParadigmStage1(Paradigm, PumpSettingsMixin):

    selector = Instance(SignalSelector, {'allow_par': True})
    pars = List(Float, [1], minlen=1, store='attribute')
    signal = DelegatesTo('selector', store='child')
    spout_sensor = Enum('touch', 'optical', store='attribute')
    TTL_fs = Float(500, unit='fs', store='attribute')

    traits_view = View(
            'spout_sensor',
            Item('pars', label='Parameters', editor=ListAsStringEditor()),
            Include('simple_pump_settings'),
            VGroup(
                Item('selector', editor=InstanceEditor(view='popup_view'),
                     style='custom', show_label=False),
                ),
            )

from enthought.traits.ui.table_column import ObjectColumn
from enthought.traits.ui.api import TableEditor, TextEditor

class ParSetting(HasTraits):

    parameter = Float(store='attribute')
    reward_duration = Float(store='attribute')
    reward_rate = Float(store='attribute')

    def __cmp__(self, other):
        return cmp(self.parameter, other.parameter)

    def __str__(self):
        return "{0}, {1}s at {2}mL/m".format(self.parameter,
                                             self.reward_duration,
                                             self.reward_rate)

table_editor = TableEditor(
        editable=True,
        deletable=True,
        show_toolbar=True,
        row_factory=ParSetting,
        columns=[
            ObjectColumn(name='parameter', label='Par'),
            ObjectColumn(name='reward_duration', label='Reward dur'),
            ObjectColumn(name='reward_rate', label='Reward rate'),
            ]
        )

class PositiveParadigm(Paradigm, PumpSettingsMixin):

    signal = Instance(Paradigm)

    parameters = List(Instance(ParSetting), [], store='child')

    parameter_order = Trait('shuffled set', choice.options, store='attribute')
    nogo_parameter = Float
    signal_selector = Instance(SignalSelector, dict(signal=Noise(duration=3,
                                                                    attenuation=20), 
                                                       title='Signal',
                                                       allow_par=True))

    signal = DelegatesTo('signal_selector', 'signal', store='child')

    min_nogo = Int(0, label='Minimum NOGO', store='attribute')
    max_nogo = Int(3, label='Maximum NOGO', store='attribute')

    # Needs to be CBool because Pytables returns numpy.bool_ type which gets
    # rejected by Bool trait
    repeat_FA = CBool(label='Repeat NOGO if FA?', store='attribute')

    signal_offset_delay = Float(0.5, unit='s', store='attribute')
    intertrial_duration = Float(0.5, unit='s', store='attribute')
    response_window_delay = Float(0, unit='s', store='attribute')
    response_window_duration = Float(1.5, unit='s', store='attribute')

    score_window_duration = Float(3, unit='s', store='attribute')
    reward_duration = Float(0.5, unit='s', store='attribute')
    #spout_smooth_duration = Float(0.25, unit='s', store='attribute')

    timeout_duration = Float(5, unit='s', store='attribute')

    poke_duration_lb = Float(0.1, unit='s', store='attribute')
    poke_duration_ub = Float(0.5, unit='s', store='attribute')

    spout_sensor = Enum('touch', 'optical', store='attribute')

    TTL_fs = Float(500, unit='fs', store='attribute')

    traits_view = View(
            'pump_syringe',
            VGroup('signal_selector{}@'),
            Item('parameter_order'),
            VGroup(
                Item('parameters', editor=table_editor),
                show_labels=False,
                ),
            Item('nogo_parameter', label='NOGO parameter'),
            'min_nogo',
            'max_nogo',
            'repeat_FA',
            'signal_offset_delay',
            'intertrial_duration',
            'response_window_delay',
            'response_window_duration',
            'score_window_duration',
            'timeout_duration',
            'spout_sensor',
            #'spout_smooth_duration',
            'poke_duration_lb',
            'poke_duration_ub',
            resizable=True,
            title='Positive paradigm editor',
            )

if __name__ == '__main__':
    #PositiveParadigmStage1().configure_traits()
    PositiveParadigm().configure_traits()

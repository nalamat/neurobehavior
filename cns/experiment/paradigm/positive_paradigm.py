from cns.experiment.paradigm.paradigm import Paradigm
from cns.signal.type import Tone, Noise
from cns.signal.signal_dialog import SignalSelector
from enthought.traits.api import Instance, Float, DelegatesTo, Int, Float, \
        Bool, Enum, List
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
                #label='Signal',
                #show_border=True,
                ),
            )

class PositiveParadigm(Paradigm, PumpSettingsMixin):

    go_signal_selector = Instance(SignalSelector, dict(signal=Noise(duration=3,
                                                                    attenuation=20), 
                                                       title='GO signal',
                                                       allow_par=False))

    nogo_signal_selector = Instance(SignalSelector, dict(signal=Tone(duration=3,
                                                                     attenuation=20,
                                                                     frequency=1000), 
                                                         title='NOGO signal',
                                                         allow_par=False))

    go_signal = DelegatesTo('go_signal_selector', 'signal', store='child')
    nogo_signal = DelegatesTo('nogo_signal_selector', 'signal', store='child')

    #go_probability = Float(0.5, store='attribute')
    min_nogo = Int(0, label='Minimum NOGO', store='attribute')
    max_nogo = Int(3, label='Maximum NOGO', store='attribute')
    repeat_FA = Bool(label='Repeat NOGO if FA?', store='attribute')

    signal_offset_delay = Float(0.5, unit='s', store='attribute')
    intertrial_duration = Float(0.5, unit='s', store='attribute')
    response_window_delay = Float(0, unit='s', store='attribute')
    response_window_duration = Float(1.5, unit='s', store='attribute')

    score_window_duration = Float(3, unit='s', store='attribute')
    reward_duration = Float(0.5, unit='s', store='attribute')
    spout_smooth_duration = Float(0.25, unit='s', store='attribute')

    timeout_duration = Float(5, unit='s', store='attribute')

    poke_duration_lb = Float(0.1, unit='s', store='attribute')
    poke_duration_ub = Float(0.5, unit='s', store='attribute')

    spout_sensor = Enum('touch', 'optical', store='attribute')

    TTL_fs = Float(500, unit='fs', store='attribute')

    traits_view = View(Include('simple_pump_settings'),
                       VGroup('go_signal_selector{}@', 
                              'nogo_signal_selector{}@',),
                       'min_nogo',
                       'max_nogo',
                       'repeat_FA',
                       'signal_offset_delay',
                       'intertrial_duration',
                       'response_window_delay',
                       'response_window_duration',
                       'score_window_duration',
                       'reward_duration',
                       'timeout_duration',
                       'spout_sensor',
                       'spout_smooth_duration',
                       'poke_duration_lb',
                       'poke_duration_ub',
                       resizable=True,
                       title='Positive paradigm editor',
                    )

if __name__ == '__main__':
    PositiveParadigmStage1().configure_traits()

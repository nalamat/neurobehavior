from cns.experiment.paradigm.paradigm import Paradigm
from cns.signal.type import Tone, Noise
from cns.signal.signal_dialog import SignalSelector
from enthought.traits.api import Instance, Float, DelegatesTo, Int, Float
from enthought.traits.ui.api import View, spring, VGroup

class PositiveParadigm(Paradigm):

    go_signal_selector = Instance(SignalSelector, dict(signal=Noise(duration=3), 
                                                       title='GO signal',
                                                       allow_par=False))

    nogo_signal_selector = Instance(SignalSelector, dict(signal=Tone(duration=3), 
                                                         title='NOGO signal',
                                                         allow_par=False))

    go_signal = DelegatesTo('go_signal_selector', 'signal', store='child')
    nogo_signal = DelegatesTo('nogo_signal_selector', 'signal', store='child')

    #go_probability = Float(0.5, store='attribute')
    min_nogo = Int(0, label='Minimum NOGO', store='attribute')
    max_nogo = Int(3, label='Maximum NOGO', store='attribute')

    intertrial_duration = Float(0.5, unit='s', store='attribute')
    response_window_delay = Float(0, unit='s', store='attribute')
    response_window_duration = Float(1.5, unit='s', store='attribute')

    score_window_duration = Float(3, unit='s', store='attribute')
    reward_duration = Float(0.5, unit='s', store='attribute')

    poke_duration_lb = Float(0.1, unit='s', store='attribute')
    poke_duration_ub = Float(0.5, unit='s', store='attribute')

    TTL_fs = Float(500, unit='fs', store='attribute')

    traits_view = View(VGroup('go_signal_selector{}@', 
                              'nogo_signal_selector{}@',),
                       #'go_probability{GO probability}',
                       'min_nogo',
                       'max_nogo',
                       'intertrial_duration',
                       'response_window_delay',
                       'response_window_duration',
                       'score_window_duration',
                       'reward_duration',
                       'poke_duration_lb',
                       resizable=True,
                       title='Positive paradigm editor',
                    )

if __name__ == '__main__':
    PositiveParadigm().configure_traits()

from cns import choice
from cns import equipment
from cns.experiment.paradigm.paradigm import Paradigm
from cns.signal import Signal
from cns.signal.signal_dialog import SignalDialog
from cns.signal.type import Tone
from cns.traits.ui.api import ListAsStringEditor
from cns.widgets import icons
from enthought.savage.traits.ui.svg_button import SVGButton
from enthought.traits.api import Button, on_trait_change, HasTraits, Any, Range, \
    CFloat, Property, Instance, Trait, Int, Dict, Float, List, Bool, Enum
from enthought.traits.ui.api import Handler, View, spring, \
    Item, InstanceEditor, ListEditor, VGroup, HGroup

import logging
log = logging.getLogger(__name__)

class SignalEditHandler(Handler):

    from enthought.etsconfig.api import ETSConfig

    if ETSConfig.toolkit == 'wx':
        edit_signal = Button('E')
    else:
        item_kw = dict(height=24, width=24)
        edit_signal = SVGButton(filename=icons.configure, 
                                tooltip='Edit Signal',
                                **item_kw)

    def handler_edit_signal_changed(self, info):
        dlg = SignalDialog(signal=info.object.signal,
                           title='Edit signal',
                           allow_par=True)
        if dlg.edit_traits(parent=info.ui.control).result:
            info.object.signal = dlg.signal

class PositiveParadigm(Paradigm):

    go_signal = Instance(Signal, Noise(), store='child')
    nogo_signal = Instance(Signal, Tone(), store='child')
    go_probability = Float(0.5)

    intertrial_duration = Float(0.5, unit='s')
    response_window_delay = Float(0, unit='s')
    response_window_duration = Float(1.5, unit='s')

    score_window_duration = Float(3, unit='s')
    reward_duration = Float(0.5, unit='s')

    poke_duration_lb = Float(0.1, unit='s')
    poke_duration_ub = Float(0.5, unit='s')

    #===========================================================================
    # The views available
    #===========================================================================
    edit_view = View(VGroup('go_signal',
                            'nogo_signal',
                            'go_probability',
                            'intertrial_duration',
                            'response_window_delay',
                            'response_window_duration',
                            'score_window_duration',
                            'reward_duration',
                            'poke_duration_lb',
                            )
                     #handler=SignalEditHandler,
                     resizable=True,
                     title='Positive paradigm editor',
                    )

if __name__ == '__main__':
    PositiveParadigm().configure_traits()

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

    spout_dur = Float(0.1, unit='s')
    poke_dur_lb = Float(0.1, unit='s')
    poke_dur_ub = Float(0.5, unit='s')
    reward_delay = Float(0, unit='s')
    reward_dur = Float(1.5, unit='s')
    timeout_dur = Float(5, unit='s')
    allow_timeout = Bool(False)

    par_order = Trait('descending', choice.options,
                      label='Parameter order',
                      store='attribute', log_change=True)

    pars = List(CFloat, [1, .5, .25, .125], 
                minlen=1,
                label='Parameters',
                editor=ListAsStringEditor(),
                store='attribute')

    signal = Instance(Signal, Tone(), store='child')

    #===========================================================================
    # The views available
    #===========================================================================
    edit_view = View(VGroup('poke_dur_lb',
                            'poke_dur_ub',
                            'spout_dur',
                            'pars',
                            'par_order',
                            HGroup(Item('signal', style='readonly'),
                                   spring, 'handler.edit_signal',
                                   show_labels=False),
                            'reward_delay',
                            'reward_dur',
                            'timeout_dur',
                            'allow_timeout',
                           ),
                     handler=SignalEditHandler,
                     resizable=True,
                     title='Positive paradigm editor',
                    )

if __name__ == '__main__':
    PositiveParadigm().configure_traits()

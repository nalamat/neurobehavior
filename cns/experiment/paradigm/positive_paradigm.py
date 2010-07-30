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
    Item, InstanceEditor, ListEditor
import logging
log = logging.getLogger(__name__)

class ParadigmSignalEditHandler(Handler):

    from enthought.etsconfig.api import ETSConfig

    if ETSConfig.toolkit == 'wx':
        edit_signal = Button('E')
    else:
        item_kw = dict(height=24, width=24)
        edit_signal = SVGButton(filename=icons.configure, tooltip='Edit Signal',
                **item_kw)

    def handler_edit_signal_changed(self, info):
        dlg = SignalDialog(signal=info.object.signal,
                           title='Edit signal',
                           allow_par=False)
        if dlg.edit_traits(parent=info.ui.control).result:
            info.object.signal = dlg.signal

class PositiveParadigm(Paradigm):

    par_order = Trait('descending', choice.options,
                      label='Parameter order',
                      store='attribute', log_change=True)
    pars = List(CFloat, [2000, 4000, 8000], 
                minlen=1,
                label='Parameters',
                editor=ListAsStringEditor(),
                store='attribute')
    par_remind = CFloat(1000,
                        label='Remind parameter',
                        store='attribute', log_change=True)

    signal = Instance(Signal, Tone(), store='child')

    #===========================================================================
    # The views available
    #===========================================================================
    def edit_view(self, parent=None):
        par_gr = ['par_remind', 'par_order', 'pars', '|[Parameters]']

        return View(par_gr, shock_gr, timing_gr,
                    ['signal{}~', spring, 'handler.edit_signal{}', '-[signal]'],
                    handler=ParadigmSignalEditHandler,
                    resizable=True,
                    title='Positive paradigm editor')

    def run_view(self, parent=None):
        par_gr = ['par_remind', 'par_order', 'pars', '|[Parameters]']
        return View(par_gr, shock_gr)

if __name__ == '__main__':
    PositiveParadigm().configure_traits()

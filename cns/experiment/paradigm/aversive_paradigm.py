from cns import choice
from cns.experiment.paradigm.paradigm import Paradigm
from cns.signal import Signal
from cns.signal.signal_dialog import SignalDialog
from cns.signal.type import Tone
from cns.traits.ui.api import ListAsStringEditor
from cns.widgets import icons
from enthought.savage.traits.ui.svg_button import SVGButton
from enthought.traits.api import Button, on_trait_change, HasTraits, Any, Range, \
    CFloat, Property, Instance, Trait, Int, Dict, Float, List, Bool
from enthought.traits.ui.api import Handler, View, spring, \
    Item, InstanceEditor, ListEditor
import logging
log = logging.getLogger(__name__)

class ParadigmSignalEditHandler(Handler):

    from enthought.etsconfig.api import ETSConfig

    if ETSConfig.toolkit == 'wx':
        edit_signal_safe = Button('E')
        edit_signal_warn = Button('E')

    else:
        item_kw = dict(height=24, width=24)
        edit_signal_safe    = SVGButton(filename=icons.configure,
                                        tooltip='Edit Safe',
                                        **item_kw)
        edit_signal_warn    = SVGButton(filename=icons.configure,
                                        tooltip='Edit Warn',
                                        **item_kw)

    def handler_edit_signal_safe_changed(self, info):
        dlg = SignalDialog(signal=info.object.signal_safe,
                           title='Edit safe signal',
                           allow_par=False)
        if dlg.edit_traits(parent=info.ui.control).result:
            info.object.signal_safe = dlg.signal

    def handler_edit_signal_warn_changed(self, info):
        dlg = SignalDialog(signal=info.object.signal_warn,
                           title='Edit warn signal',
                           allow_par=True)
        if dlg.edit_traits(parent=info.ui.control).result:
            info.object.signal_warn = dlg.signal

class ShockSettings(HasTraits):

    class Setting(HasTraits):
        par = Float
        level = Range(0.0, 1, 0)
        def __cmp__(self, other):
            if type(other) == type(self):
                return self.par-other.par
            else:
                return self.par-other
        def __hash__(self):
            return self.par.__hash__()
        def __repr__(self):
            return'Setting(par=%f, level=%f)' % (self.par, self.level)
        traits_view = View(['par{}~', 'level{}', '-'])

    paradigm = Any
    max_shock = Range(0.0, 5.0, 2.5, store='attribute')

    levels = List(Setting)
    #cache = Dict(Float, Setting, store='attribute')
    cache = Dict(Float, Float, store='attribute')
    
    def update(self):
        self.levels = []
        self._add_pars(self.paradigm.pars)

    @on_trait_change('paradigm')
    def _paradigm_changed(self, new):
        self.update()

    @on_trait_change('paradigm:pars')
    def _new_items(self, object, name, old, new):
        if old:
            for par in old:
                self.levels.remove(par)
        if new:
            self._add_pars(new)
            
    def _add_pars(self, pars):
        for par in pars:
            level = self.cache.setdefault(par, 0)
            self.levels.append(self.Setting(par=par, level=level))
        self.levels.sort()

    def get_level(self, par):
        return self.cache[par]*self.max_shock

    editor = ListEditor(editor=InstanceEditor(), mutable=False, style='custom')
    traits_view = View([['max_shock{Maximum shock}'],
                        Item('levels{}', editor=editor), '|[Shock settings]'],
                       resizable=True)

class AversiveParadigm(Paradigm):

    par_order = Trait('descending', choice.options,
                      label='Parameter order',
                      store='attribute', log_change=True)
    pars = List(CFloat, [2000, 4000, 8000], minlen=1,
                        label='Parameters',
                        editor=ListAsStringEditor(),
                        store='attribute')
    par_remind = CFloat(1000,
                        label='Remind parameter',
                        store='attribute', log_change=True)
    lick_th = Range(0.0, 1.0, 0.75,
                    label='Contact threshold',
                    store='attribute', log_change=True)
    shock_settings = Instance(ShockSettings,
                           label='Shock level (V)',
                           store='child', log_change=True)

    def _shock_settings_default(self):
        return ShockSettings(paradigm=self)

    #default_pump_rate       = CFloat(0.3, store='attribute')

    # Actual lick_fs depends on the system clock.  We can only downsample at
    # multiples of the clock.
    requested_lick_fs = CFloat(500, store='attribute')

    # We set this to -1 so we know that it hasn't been set yet as we can never
    # have a negative sampling rate.
    actual_lick_fs = CFloat(-1, store='attribute')
    shock_delay = CFloat(1, store='attribute', label='Shock delay (s)')

    # Currently the shock duration cannot be controlled because it is hard
    # wired into the shock controller/spout contact circuitry.
    #shock_duration          = CFloat(0.3)

    min_safe = Int(2, store='attribute', label='Min safe trials')
    max_safe = Int(4, store='attribute', label='Max safe trials')

    signal_safe = Instance(Signal, Tone(), store='child')
    signal_warn = Instance(Signal, Tone(), store='child')

    #===========================================================================
    # Error checks
    #===========================================================================
    err_num_trials = Property(Bool, depends_on='min_safe, max_safe')
    err_signal_warn = Property(Bool, depends_on='signal_warn, signal_warn.variable')
    err_par_string = Bool(False)

    mesg_signal_warn = 'Warn signal must have one variable'
    mesg_num_trials = 'Max trials must be >= min trials'

    def _get_err_signal_warn(self):
        return self.signal_warn.variable is None
        #return len(self.signal_warn.variables) != 1

    def _get_err_num_trials(self):
        return self.min_safe > self.max_safe

    #===========================================================================
    # The views available
    #===========================================================================
    def edit_view(self, parent=None):
        par_gr = ['par_remind', 'par_order', 'pars', '|[Parameters]']
        shock_gr = Item('shock_settings{}@')

        timing_gr = [['{Num safe trials:}',
                      Item('min_safe{}', invalid='err_num_trials'), '{to}',
                      Item('max_safe{}', invalid='err_num_trials'), '-'],
                      'shock_delay', 'lick_th{Contact threshold}', '|[Trial settings]']

        return View(par_gr, shock_gr, timing_gr,
                    ['signal_safe{}~', spring, 'handler.edit_signal_safe{}', '-[SAFE signal]'],
                    ['signal_warn{}~', spring, 'handler.edit_signal_warn{}', '-[WARN signal]'],
                    handler=ParadigmSignalEditHandler,
                    resizable=True,
                    title='Aversive paradigm editor')

    def run_view(self, parent=None):
        par_gr = ['par_remind', 'par_order', 'pars', '|[Parameters]']
        shock_gr = Item('shock_settings{}@')
        return View(par_gr, shock_gr)
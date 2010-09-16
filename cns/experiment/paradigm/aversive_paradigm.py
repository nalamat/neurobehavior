from cns import choice
from cns import equipment
from cns.traits.ui.api import ListAsStringEditor
from cns.signal.signal_dialog import SignalSelector
from cns.experiment.paradigm.paradigm import Paradigm
from cns.signal.type import Tone
from enthought.traits.api import Button, on_trait_change, HasTraits, Any, Range, \
    CFloat, Property, Instance, Trait, Int, Dict, Float, List, Bool, Enum, \
    DelegatesTo
from enthought.traits.ui.api import View, Item, VGroup, Include

class BaseAversiveParadigm(Paradigm):
    '''Defines an aversive paradigm, but not the signals that will be used.
    This allows us to use either a generic circuit with two buffers for the
    warn/safe signal, or a circuit that is specialized for a specific kind of
    signal (e.g. FM).
    '''

    contact_method = Enum('touch', 'optical', store='attribute')

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

    #===========================================================================
    # Error checks
    #===========================================================================
    err_num_trials = Property(Bool, depends_on='min_safe, max_safe')
    err_par_string = Bool(False)

    mesg_signal_warn = 'Warn signal must have one variable'
    mesg_num_trials = 'Max trials must be >= min trials'

    def _get_err_num_trials(self):
        return self.min_safe > self.max_safe

    #===========================================================================
    # The views available
    #===========================================================================
    par_group = VGroup('par_remind', 'par_order', 'pars', 
                       show_border=True, label='Parameters')
    trial_group = VGroup(Item('min_safe', label='', invalid='err_num_trials'),
                         Item('max_safe', label='', invalid='err_num_trials'),)
    timing_group = VGroup(trial_group, 'shock_delay', 'lick_th', 
                          show_border=True, label='Trial settings')

    edit_view = View(VGroup(par_group, timing_group, Include('signal_group')),
                     resizable=True,
                     title='Aversive Paradigm editor')

    run_view = View(par_group)

    def run_view(self, parent=None):
        par_gr = ['par_remind', 'par_order', 'pars', '|[Parameters]']
        shock_gr = Item('shock_settings{}@')
        return View(par_gr, shock_gr)

class AversiveParadigm(BaseAversiveParadigm):
    '''Generic aversive paradigm designed to work with most classe of signals.
    Note that this will not work well with modulated tones!
    '''

    signal_safe_selector = Instance(SignalSelector, {'allow_par': False},
                                    label='Safe signal')
    signal_safe = DelegatesTo('signal_safe_selector', 'signal', store='child')
    signal_warn_selector = Instance(SignalSelector, (), label='Warn signal')
    signal_warn = DelegatesTo('signal_warn_selector', 'signal', store='child')

    signal_group = VGroup(Item('signal_safe_selector', style='custom'),
                          Item('signal_warn_selector', style='custom'))

    err_signal_warn = Property(Bool, 
                               depends_on='signal_warn, signal_warn.variable')

    def _get_err_signal_warn(self):
        return self.signal_warn.variable is None

class AversiveFMParadigm(BaseAversiveParadigm):
    '''Aversive paradigm designed exclusively for FM tones.  Be sure to use with
    the appropriate DSP circuit.
    '''

    center_frequency = Float(4000, store='attribute')
    attenuation = Range(0, 120, 40, store='attribute')

    signal_group = VGroup('center_frequency', 'attenuation', 
                          show_border=True, label='FM parameters')

if __name__ == '__main__':
    AversiveParadigm().configure_traits(view='edit_view')

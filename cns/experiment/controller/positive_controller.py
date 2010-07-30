from .experiment_controller import ExperimentController
from cns import choice, equipment
from cns.data.h5_utils import append_node, append_date_node, \
    get_or_append_node
from cns.data.persistence import add_or_update_object
from cns.experiment.data import AversiveData
from cns.experiment.paradigm import AversiveParadigm
from cns.widgets import icons
from cns.widgets.toolbar import ToolBar
from datetime import timedelta, datetime
from enthought.etsconfig.etsconfig import ETSConfig
from enthought.pyface.api import error
from enthought.pyface.timer.api import Timer
from enthought.savage.traits.ui.svg_button import SVGButton
from enthought.traits.api import Any, Instance, CInt, CFloat, Str, Float, \
    Property, HasTraits, Bool, on_trait_change, Dict, Button, Event
from enthought.traits.ui.api import HGroup, spring, Item, View
import logging
import time
import numpy as np

log = logging.getLogger(__name__)

class CurrentSettings(HasTraits):

    paradigm = Instance(PostiveParadigm)
    
    '''Tracks the trial index for comparision with the circuit index'''
    idx = CInt(0)

    '''Number of safe trials''' 
    safe_trials = CInt
    '''The trial we are going to, or currently, presenting'''
    trial = CInt

    '''Parameter to present'''
    par = CFloat
    par_remind = CFloat

    _choice_num_safe = Any
    _choice_par = Any
    _signal_cache = {}

    signal_warn = Property
    signal_remind = Property

    def __init__(self, **kw):
        super(CurrentSettings, self).__init__(**kw)
        self.initialize(self.paradigm)

    def reset(self):
        self.initialize(self.paradigm)

    def initialize(self, paradigm):
        self._choice_par = self._get_choice_par(paradigm)
        self._choice_num_safe = self._get_choice_num_safe(paradigm)
        self._signal_cache = build_signal_cache(self.signal_warn,
                                                paradigm.par_remind,
                                                *paradigm.pars)

        self.build_shock_level_cache(paradigm)
        self.par_remind = paradigm.par_remind
        self.next()

    def next(self):
        self.par = self._choice_par.next()
        self.safe_trials = self._choice_num_safe.next()
        self.trial = 1
        self.shock_level = self.paradigm.shock_settings.get_level(self.par)

    #===========================================================================
    # Helpers for run-time control of experiment
    #===========================================================================
    def _get_signal(self):
        return self._signal_warn_cache[self.par]

    def _get_choice_par(self, paradigm):
        # Always pass a copy of pars to other functions that may modify the
        # content of the list
        return choice.get(paradigm.par_order, paradigm.pars[:])

class PositiveController(ExperimentController):

    toolbar = Instance(AversiveToolBar, ())

    backend = Any
    circuit = Any
    pump = Any

    exp_node = Any
    data_node = Any

    # Will be used to poll the state of the hardware every few milliseconds and
    # update the view as needed (i.e. download lick data, upload new signal
    # waveforms, etc).  See timer_tick.
    fast_timer = Instance(Timer)
    slow_timer = Instance(Timer)

    # A coroutine pipeline that acquires contact data from the RX6 and sends it
    # to the TrialData object
    data_pipe = Any
    start_time = Float
    completed = Bool(False)
    water_infused = Float(0)

    status = Property(Str, depends_on='current.trial, current.par, current.safe_trials, state')
    time_elapsed = Property(Str, depends_on='slow_tick', label='Time')

    slow_tick = Event
    fast_tick = Event

    def init(self, info):
        # Install the toolbar handler
        self.model = info.object
        self.toolbar.install(self, info)
        try:
            self.init_equipment(info)
        except equipment.EquipmentError, e:
            self.state = 'disconnected'
            error(info.ui.control, str(e))

    def init_equipment(self, info):
        self.pump = equipment.pump().Pump()
        self.backend = equipment.dsp()
        self.circuit = self.backend.load('positive-behavior', 'RX6')

    def configure_circuit(self, circuit, paradigm):
        if circuit is None:
            return
        elif circuit.running:
            raise SystemError, 'Cannot configure circuit while it is running'

        # This is an example of the "handler" approach.  The model
        # ('paradigm') does not have to concern itself about how the
        # equipment needs to be configured.  If we ever get a new set of
        # hardware, this code would be the only stuff that needs changing.
        circuit.reload()

        circuit.pretrial_delay_n.set(paradigm.pretrial_delay, 'msec')
        circuit.reward_delay_n.set(paradigm.reward_delay, 'msec')
        circuit.reward_duration_n.set(paradigm.reward_duration, 'msec')

    def run(self, info=None):
        if not self.model.paradigm.is_valid():
            mesg = 'Please correct the following errors first:\n'
            mesg += self.model.paradigm.err_messages()
            error(self.info.ui.control, mesg)
            return

        try:
            # Order is important.  The data depends on several properties set in
            # the circuit, so initialize_data must be called after
            # initialize_circuit
            self.configure_circuit(self.circuit, self.model.paradigm)

            #===================================================================
            # Finally, everything's a go!
            #===================================================================
            self.fast_timer = Timer(250, self.tick, 'fast')
            self.slow_timer = Timer(1000, self.tick, 'slow')

            # Setting state to paused should be one of the last things we do to
            # prevent the UI from changing the controls to the 'running' state.
            self.state = 'paused'
            self.circuit.start()

        except BaseException, e:
            self.state = 'halted'
            error(self.info.ui.control, str(e))
            raise

    def remind(self, info=None):
        self.state = 'manual'
        # The actual sequence is important.  We must finish uploading the signal
        # before we set the circuit flags to allow commencement of a trial.

        self.circuit.target_signal.set(self.current.target_signal)
        self.backend.set_attenuation(self.current.signal_remind.attenuation, 'PA5')
        self.circuit.pause_state.value = False # Everything's ready. GO!
        self.circuit.trigger(1)

    def stop(self, info=None):
        self.state = 'halted'
        self.slow_timer.stop()
        self.fast_timer.stop()
        self.circuit.stop()
        self.pending_changes = {}
        self.old_values = {}

    #===========================================================================
    # Tasks driven by the slow and fast timers
    #===========================================================================
    @on_trait_change('slow_tick')
    def task_update_pump(self):
        infused = self.pump.infused
        self.model.data.log_water(self.circuit.ts_n.value, infused)
        self.water_infused = infused

    def _get_status(self):
        if self.state == 'disconnected':
            return 'Cannot connect to equipment'
        if self.state == 'halted':
            return 'System is halted'
        if self.state == 'manual':
            return 'PAUSED: presenting reminder (%r)' % self.current.par

        if self.current.trial > self.current.safe_trials:
            status = 'WARNING (%r)' % self.current.par
        else:
            mesg = 'SAFE %d of %d (%r)'
            status = mesg % (self.current.trial, self.current.safe_trials, self.current.par)
        if self.state == 'paused':
            status = 'PAUSED: next trial is %s' % status
        return status

    @on_trait_change('pump.rate')
    def log_pump(self, new):
        if self.state <> 'halted':
            self.model.data.log_event(self.circuit.ts_n.value, 'pump rate', new)

    ############################################################################
    # Code to apply parameter changes
    ############################################################################
    def _reset_current(self, value):
        self.current.reset()

    _apply_lick_th = _reset_current
    _apply_par_order = _reset_current
    _apply_par_remind = _reset_current
    _apply_pars = _reset_current
    _apply_level = _reset_current
    _apply_levels_items = _reset_current

    def _apply_lick_th(self, value):
        self.circuit.lick_th.value = value

    def _apply_contact_method(self, value):
        if value == 'touch':
            self.circuit.contact_method.value = 0
        else:
            self.circuit.contact_method.value = 1

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

    '''Parameter to present'''
    par = CFloat
    _choice_par = Any
    _signal_cache = {}

    def __init__(self, **kw):
        super(CurrentSettings, self).__init__(**kw)
        self.initialize(self.paradigm)

    def reset(self):
        self.initialize(self.paradigm)

    def initialize(self, paradigm):
        self._choice_par = self._get_choice_par(paradigm)
        self._signal_cache = build_signal_cache(self.signal_warn,
                                                paradigm.par_remind,
                                                *paradigm.pars)
        self.next()

    def next(self):
        self.par = self._choice_par.next()

    #===========================================================================
    # Helpers for run-time control of experiment
    #===========================================================================
    def _get_signal(self):
        return self._signal_cache[self.par]

    def _get_choice_par(self, paradigm):
        # Always pass a copy of pars to other functions that may modify the
        # content of the list
        return choice.get(paradigm.par_order, paradigm.pars[:])

class PositiveController(ExperimentController):

    toolbar = Instance(AversiveToolBar, ())

    backend = Any
    circuit = Any
    pump = Any

    fast_timer = Instance(Timer)

    # A coroutine pipeline that acquires contact data from the RX6 and sends it
    # to the TrialData object
    data_pipe = Any
    start_time = Float
    completed = Bool(False)
    water_infused = Float(0)

    status = Property(Str, depends_on='currentnt.par, state')
    time_elapsed = Property(Str, depends_on='slow_tick', label='Time')

    fast_tick = Event

    def init_equipment(self, info):
        self.pump = equipment.pump().Pump()
        self.backend = equipment.dsp()
        self.circuit = self.backend.load('positive-behavior', 'RX6')

    def configure_circuit(self, circuit, paradigm):
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
            self.configure_circuit(self.circuit, self.model.paradigm)
            self.fast_timer = Timer(250, self.tick, 'fast')
            self.circuit.start()
        except BaseException, e:
            self.state = 'halted'
            error(self.info.ui.control, str(e))
            raise

    def remind(self, info=None):
        self.state = 'manual'
        signal = self.current.target_signal
        self.circuit.target_signal.set(signal)
        self.backend.set_attenuation(signal.attenuation, 'PA5')
        self.circuit.trigger(1)

    def stop(self, info=None):
        self.state = 'halted'
        self.fast_timer.stop()
        self.circuit.stop()
        self.pending_changes = {}
        self.old_values = {}

    #===========================================================================
    # Tasks driven by the slow and fast timers
    #===========================================================================
    @on_trait_change('slow_tick')
    def task_update_pump(self):
        self.water_infused = self.pump.infused

    def _get_status(self):
        if self.state == 'disconnected':
            return 'Cannot connect to equipment'
        if self.state == 'halted':
            return 'System is halted'
        return 'Target (%r)' % self.current.par

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

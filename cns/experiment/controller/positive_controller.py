from .experiment_controller import ExperimentController
from cns import choice, equipment
from cns.data.h5_utils import append_node, append_date_node, \
    get_or_append_node
from cns.data.persistence import add_or_update_object
from cns.experiment.data.positive_data import PositiveData
from cns.experiment.paradigm.positive_paradigm import PositiveParadigm
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
from cns.experiment.controller.experiment_controller import build_signal_cache

log = logging.getLogger(__name__)

class CurrentSettings(HasTraits):

    paradigm = Instance(PositiveParadigm, ())
    signal = Property
    
    '''Tracks the trial index for comparision with the circuit index'''
    idx = CInt(0)

    '''Parameter to present'''
    par = CFloat
    _choice_par = Any
    _signal_cache = {}

    def __init__(self, **kw):
        super(CurrentSettings, self).__init__(**kw)
        self.initialize()

    def reset(self):
        self.initialize()

    def initialize(self):
        self._choice_par = self._get_choice_par()
        self._signal_cache = build_signal_cache(self.paradigm.signal,
                                                *self.paradigm.pars)
        self.next()

    def next(self):
        self.par = self._choice_par.next()

    #===========================================================================
    # Helpers for run-time control of experiment
    #===========================================================================
    def _get_signal(self):
        return self._signal_cache[self.par]

    def _get_choice_par(self):
        # Always pass a copy of pars to other functions that may modify the
        # content of the list
        return choice.get(self.paradigm.par_order, self.paradigm.pars[:])

class PositiveController(ExperimentController):

    current = Instance(CurrentSettings)

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

    status = Property(Str, depends_on='current.par, state')

    fast_tick = Event

    def init_equipment(self, info):
        self.pump = equipment.pump().Pump()
        self.backend = equipment.dsp()
        self.circuit = self.backend.load('positive-behavior-stage1', 'RX6')

    def configure_circuit(self, circuit, paradigm):
        circuit.reload()
        circuit.trial_delay_n.set(paradigm.trial_delay, 's')
        circuit.reward_delay_n.set(paradigm.reward_delay, 's')
        circuit.reward_dur_n.set(paradigm.reward_dur, 's')
        circuit.contact_buf.initialize()
        circuit.trial_running_buf.initialize()
        circuit.reward_running_buf.initialize()

    def start(self, info=None):
        if not self.model.paradigm.is_valid():
            mesg = 'Please correct the following errors first:\n'
            mesg += self.model.paradigm.err_messages()
            error(self.info.ui.control, mesg)
            return

        try:
            self.configure_circuit(self.circuit, self.model.paradigm)
            self.fast_timer = Timer(250, self.tick, 'fast')
            self.current = CurrentSettings(paradigm=self.model.paradigm)
            self.state = 'paused'
            self.circuit.start()
        except BaseException, e:
            self.state = 'halted'
            error(self.info.ui.control, str(e))
            raise

    def remind(self, info=None):
        self.state = 'manual'
        signal = self.current.signal
        self.circuit.trial_buf.set(signal)
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

    @on_trait_change('fast_tick')
    def monitor_buffers(self):
        self.model.data.optical_digital.send(self.circuit.contact_buf.read())
        self.model.data.trial_running.send(self.circuit.trial_running_buf.read())
        self.model.data.reward_running.send(self.circuit.reward_running_buf.read())

    @on_trait_change('fast_tick')
    def monitor_circuit(self):
        if self.circuit.trial_idx.value > self.current.idx:
            self.current.idx += 1
            if self.state == 'manual':
                self.state = 'paused'
                self.current.next()

    ############################################################################
    # Code to apply parameter changes
    ############################################################################
    def _apply_trial_delay(self, value):
        self.circuit.trial_delay_n.set(value, 's')

    def _apply_reward_delay(self, value):
        self.circuit.reward_delay_n.set(value, 's')

    def _apply_reward_dur(self, value):
        self.circuit.reward_dur_n.set(value, 's')

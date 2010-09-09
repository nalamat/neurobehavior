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
    Property, HasTraits, Bool, on_trait_change, Dict, Button, Event, Range
from enthought.traits.ui.api import HGroup, spring, Item, View
import logging
import time
import numpy as np
from cns.experiment.controller.experiment_controller import build_signal_cache

log = logging.getLogger(__name__)

class PositiveController(ExperimentController):

    backend = Any
    circuit = Any
    pump = Any

    fast_timer = Instance(Timer)

    start_time = Float
    completed = Bool(False)
    water_infused = Float(0)
    attenuation = Range(0, 120, 30)

    fast_tick = Event

    def init_equipment(self, info):
        self.pump = equipment.pump().Pump()
        self.backend = equipment.dsp()
        self.circuit = self.backend.load('positive-behavior-stage1', 'RX6')

    def start(self, info=None):
        self._attenuation_changed(self.attenuation)
        try:
            self.circuit.reload()
            self.circuit.contact_buf.initialize()
            self.fast_timer = Timer(250, self.tick, 'fast')
            self.state = 'running'
            self.circuit.start()
        except BaseException, e:
            self.state = 'halted'
            error(self.info.ui.control, str(e))
            raise

    def stop(self, info=None):
        self.state = 'halted'
        self.fast_timer.stop()
        self.circuit.stop()

    def resume(self, info=None):
        self.state = 'running'
        self.circuit.running.value = True

    def pause(self, info=None):
        self.state = 'paused'
        self.circuit.running.value = False

    def _attenuation_changed(self, new):
        self.backend.set_attenuation(new, 'PA5')

    #===========================================================================
    # Tasks driven by the slow and fast timers
    #===========================================================================
    @on_trait_change('slow_tick')
    def task_update_pump(self):
        self.water_infused = self.pump.infused

    @on_trait_change('fast_tick')
    def monitor_buffers(self):
        self.model.data.optical_digital.send(self.circuit.contact_buf.read())

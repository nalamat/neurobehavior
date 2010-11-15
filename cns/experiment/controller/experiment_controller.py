from cns import equipment
from cns.widgets import icons
from cns.widgets.toolbar import ToolBar
from enthought.etsconfig.api import ETSConfig
from enthought.pyface.api import error
from enthought.savage.traits.ui.svg_button import SVGButton
from enthought.traits.api import Enum, Int, Instance, Dict, on_trait_change, \
    Property, Str, Button, Tuple, Any, Event, List
from enthought.traits.ui.api import Controller, Handler, HGroup, Item, spring, \
    View
from enthought.pyface.timer.api import Timer
from datetime import datetime, timedelta

import logging
log = logging.getLogger(__name__)

class ExperimentToolBar(ToolBar):

    size = 24, 24

    if ETSConfig.toolkit == 'qt4':
        kw      = dict(height=size[0], width=size[1], action=True)
        apply   = SVGButton('Apply', filename=icons.apply,
                            tooltip='Apply settings', **kw)
        revert  = SVGButton('Revert', filename=icons.undo,
                            tooltip='Revert settings', **kw)
        start   = SVGButton('Run', filename=icons.start,
                            tooltip='Begin experiment', **kw)
        pause   = SVGButton('Pause', filename=icons.pause,
                            tooltip='Pause', **kw)
        resume  = SVGButton('Resume', filename=icons.resume,
                            tooltip='Resume', **kw)
        stop    = SVGButton('Stop', filename=icons.stop,
                            tooltip='stop', **kw)
        remind  = SVGButton('Remind', filename=icons.warn,
                            tooltip='Remind', **kw)
        item_kw = dict(show_label=False)
    else:
        # The WX backend renderer for SVG buttons is ugly, so let's use text
        # buttons instead.  Eventually I'd like to unite these under ONE
        # backend.
        apply   = Button('A', action=True)
        revert  = Button('R', action=True)
        start   = Button('>>', action=True)
        pause   = Button('||', action=True)
        resume  = Button('>', action=True)
        stop    = Button('X', action=True)
        remind  = Button('!', action=True)
        item_kw = dict(show_label=False, height=-size[0], width=-size[1])

    traits_view = View(
            HGroup(Item('apply',
                        enabled_when="object.handler.pending_changes<>{}",
                        **item_kw),
                   Item('revert',
                        enabled_when="object.handler.pending_changes<>{}",
                        **item_kw),
                   Item('start',
                        enabled_when="object.handler.state=='halted'",
                        **item_kw),
                   '_',
                   Item('remind',
                        enabled_when="object.handler.state=='paused'",
                        **item_kw),
                   Item('pause',
                        enabled_when="object.handler.state=='running'",
                        **item_kw),
                   Item('resume',
                        enabled_when="object.handler.state=='paused'",
                        **item_kw),
                   Item('stop',
                        enabled_when="object.handler.state in " +\
                                     "['running', 'paused', 'manual']",
                        **item_kw),
                   spring,
                   springy=True,
                   ),
            kind='subpanel',
            )

from pump_controller_mixin import PumpToolBar

class ExperimentController(Controller):
    """Primary controller for TDT System 3 hardware.  This class must be
    configured with a model that contains the appropriate parameters (e.g.
    Paradigm) and a view to show these parameters.

    As changes are applied to the view, the necessary changes to the hardware
    (e.g. RX6 tags and PA5 attenuation) will be made and the model will be
    updated.

    For a primer on model-view-controller architecture and its relation to the
    Enthought libraries (e.g. Traits), refer to the Enthought Tool Suite
    documentation online at:
    https://svn.enthought.com/enthought/wiki/UnderstandingMVCAndTraitsUI

    The controller has one of several states:
    Halted
        The system is waiting for the user to configure parameters.  No data
        acquisition is in progress nor is a signal being played.  
    Paused
        The system is configured, spout contact is being monitored, and the
        intertrial signal is being played. 
    Manual
        The user has requested a manual trial.  Once the trial is over, the
        controller will go back to the paused state.
    Running
        The system is playing the sequence of safe and warn signals. 
    Complete
        The experiment is done.
    Disconnected
        Could not connect to the equipment.

    The controller listens for changes to paradigm parameters.  All requested
    changes are intercepted and cached.  If a parameter is changed several times
    (before applying or reverting), the cache is updated with the most recent
    value.  To make a parameter configurable during an experiment it must
    either:
    - Have a function handler named `_apply_<parameter name>` that takes the new
      value of the parameter and performs the necessary logic to update the
      experiment state.
    - Have an entry in `parameter_map` 

    If both methods of configuring a parameter are present, the first method
    encountered (i.e. `_apply_<parameter name>`) takes precedence.  If the
    change is not allowed, a warning will be raised (but the handler will
    continue running).  If a parameter is not configurable, be sure to set the
    view accordingly (e.g. hide or disable the field).

    Very important!  To ensure that your controller logic ties in cleanly with
    the apply/revert mechanism, never read values directly from the paradigm
    itself.  Always make a copy of the variable and store it elsewhere (e.g. in
    the controller object) and create an apply handler to update the copy of the
    variable from the paradigm.

    Typically handlers need to work closely with a DSP device.
    """

    toolbar = Instance(ExperimentToolBar, (), toolbar=True)
    pt = Instance(PumpToolBar, (), toolbar=True)
    
    state = Enum('halted', 'paused', 'running', 'manual', 'disconnected',
                 'complete')

    """Dictionary of circuits to be loaded.  Keys correspond to the name the
    DSPCircuit object will be bound to on the controller.  Value is a tuple of
    the circuit name (and path if not on the default search path) and the target
    DSP.  For example:

    >>> circuits = { 'circuit': ('positive-behavior-stage3', 'RX6') }
    """
    circuits = Dict(Str, Tuple(Str, Str))
    backend = Any

    """Map of paradigm parameters with their corresponding circuit value (if
    applicable).  Value should be in the format circuit_name.tag_name where
    circuit_name is a reference to the name specified in
    `ExperimentController.circuits`.
    """
    parameter_map = Dict

    start_time = Instance(datetime)
    time_elapsed = Property(Instance(timedelta), depends_on='slow_tick')

    timer = Instance('enthought.pyface.timer.api.Timer')

    def init(self, info):
        '''Post-construction init.  Determines whether it is able to connect
        with the hardware.'''
        log.debug("Initializing equipment")
        try:
            self.model = info.object
            for toolbar in self.trait_names(toolbar=True):
                getattr(self, toolbar).install(self, info)
                print getattr(self, toolbar)
            self.init_equipment(info)
            log.debug("Successfully initialized equipment")
        except equipment.EquipmentError, e:
            log.error(e)
            self.state = 'disconnected'
            error(info.ui.control, str(e))

    def init_equipment(self, info):
        '''Attempts to connect with the hardware.  Called when the class is
        first constructed.'''
        self.init_dsp(info)

    def init_experiment(self, info):
        '''Called when start is pressed.  Place paradigm-specific initialization
        code here.
        '''
        for name in self.circuits:
            getattr(self, name).reload()
        self.autoconfigure_dsp_tags(self.model.paradigm, info)
        self.start_time = datetime.now()

    def init_dsp(self, info):
        '''Loads circuits specified in `circuits`'''
        log.debug("Loading DSP backend")
        self.backend = equipment.dsp()
        log.debug("Loading circuits")
        for name, values in self.circuits.items():
            log.debug("loading %s to %s as %s", values[0], values[1], name)
            circuit = self.backend.load(*values)
            setattr(self, name, circuit)

    def autoconfigure_dsp_tags(self, paradigm, info):
        '''Using the parameter map provided, automatically configure circuit
        variables or call the appropriate function.
        '''
        for par, ref in self.parameter_map.items():
            self.autoconfigure_dsp_tag(par, ref, paradigm)

    def autoconfigure_dsp_tag(self, par, ref, paradigm):
        obj_name, ref_name = ref.split('.')
        value = getattr(paradigm, par)
        if obj_name == 'handler':
            getattr(self, ref_name)(value)
        else:
            circuit = getattr(self, obj_name)
            unit = paradigm.trait(par).unit
            log.debug('autoconfigure_dsp_tags: tag %s set to %r %r',
                      ref_name, value, unit)
            getattr(circuit, ref_name).set(value, unit)

    def _get_time_elapsed(self):
        if self.state is 'halted':
            return timedelta()
        else:
            return datetime.now()-self.start_time

    def close(self, info, is_ok):
        '''Prevent user from closing window while an experiment is running since
        data is not saved to file until the stop button is pressed.
        '''
        if self.state not in ('disconnected', 'halted', 'complete'):
            mesg = 'Please halt experiment before attempting to close window.'
            error(info.ui.control, mesg)
            return False
        else:
            return True    

    def start(self, info=None):
        '''
        Handles starting an experiment

        Subclasses must implement `start_experiment`
        '''
        if not self.model.paradigm.is_valid():
            mesg = 'Please correct the following errors first:\n'
            mesg += self.model.paradigm.err_messages()
            error(self.info.ui.control, mesg)
        try:
            self.init_experiment(info)
            self.start_experiment(info)
            #self.timer_tick = 0
            self.timer = Timer(250, self.tick)
        except BaseException, e:
            error(self.info.ui.control, str(e))
            raise

    def stop(self, info=None):
        try:
            self.timer.Stop()
        except AttributeError:
            self.timer.stop()
        self.stop_experiment(info)

        self.pending_changes = {}
        self.old_values = {}

        info.ui.view.close_result = True
        self.state = 'complete'

    ############################################################################
    # Stubs to implement
    ############################################################################
    def resume(self, info=None):
        error(info.ui.control, 'This action has not been implemented yet')
        raise NotImplementedError

    def pause(self, info=None):
        error(info.ui.control, 'This action has not been implemented yet')
        raise NotImplementedError

    def remind(self, info=None):
        error(info.ui.control, 'This action has not been implemented yet')
        raise NotImplementedError

    ############################################################################
    # Apply/Revert code
    ############################################################################
    pending_changes = Dict({})
    old_values = Dict({})

    @on_trait_change('model.paradigm.+', post_init=True)
    def queue_change(self, object, name, old, new):
        if self.state <> 'halted':
            key = object, name
            if key not in self.old_values:
                self.old_values[key] = old
                self.pending_changes[key] = new
            elif new == self.old_values[key]:
                del self.pending_changes[key]
                del self.old_values[key]
            else:
                self.pending_changes[key] = new

    def apply(self, info=None):
        try:
            ts = self.circuit.ts_n.value
        except:
            ts = -1
        print self.pending_changes
        for key, value in self.pending_changes.items():
            log.debug("Apply: setting %s to %r", key, value)
            object, name = key
            try:
                getattr(self, '_apply_'+name)(value)
                self.log_event(ts, name, value)
            except TypeError:
                try:
                    ref = self.parameter_map[name]
                    self.autoconfigure_dsp_tag(name, ref, self.model.paradigm)
                except KeyError:
                    log.warn("Can't set %s to %r", name, value)
                    log.warn("Removing this from the stack")
            del self.pending_changes[(object, name)]
            del self.old_values[(object, name)]

    def log_event(self, ts, name, value):
        raise NotImplementedError
        
    def revert(self, info=None):
        '''Revert changes requested while experiment is running.'''
        for (object, name), value in self.old_values.items():
            log.debug('reverting changes for %s', name)
            setattr(object, name, value)
        self.old_values = {}
        self.pending_changes = {}

    def _apply_circuit_change(self, name, value, circuit=None):
        setattr(self.circuit, name, value)

if __name__ == '__main__':
    ExperimentToolBar().configure_traits()

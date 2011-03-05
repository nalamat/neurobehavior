from copy import deepcopy
from datetime import datetime, timedelta

from enthought.pyface.api import error, confirm, YES
from enthought.pyface.timer.api import Timer
from enthought.etsconfig.api import ETSConfig
from enthought.traits.api import Any, Instance, Enum, Dict, on_trait_change, \
        HasTraits, List, Button
from enthought.traits.ui.api import Controller, View, HGroup, Item, spring

from cns.widgets.toolbar import ToolBar
from enthought.savage.traits.ui.svg_button import SVGButton
from cns.widgets import icons

import logging
log = logging.getLogger(__name__)

class ExperimentToolBar(ToolBar):

    size = 24, 24

    # We protect this import since we only need it for the Qt4 toolkit.  We
    # don't want this imported if we use the WX backend.
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

class AbstractExperimentController(Controller):
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
    value.  To make a parameter configurable during an experiment it must have a
    function handler named `_apply_<parameter name>` that takes the new value of
    the parameter and performs the necessary logic to update the experiment
    state.

    If the change is not allowed, a warning will be raised (but the handler will
    continue running).  If a parameter is not configurable, be sure to set the
    view accordingly (e.g. hide or disable the field) so the user knows why the
    change isn't getting applied.

    Very important!  To ensure that your controller logic ties in cleanly with
    the apply/revert mechanism, never read values directly from the paradigm
    itself.  Always make a copy of the variable and store it elsewhere (e.g. in
    the controller object) and create an apply handler to update the copy of the
    variable from the paradigm.
    """

    toolbar = Instance(ExperimentToolBar, (), toolbar=True)
    
    state = Enum('halted', 'paused', 'running', 'manual', 'disconnected',
                 'complete')

    # name_ = Any are Trait wildcards
    # see http://code.enthought.com/projects/traits/docs
    # /html/traits_user_manual/advanced.html#trait-attribute-name-wildcard)
    timer_ = Any

    # current_* and choice_* are variables tracked by the controller to
    # determine the current "state" of the experiment and what values to use for
    # the next trial. While these could be stored in the model (i.e. the
    # paradigm object), they are transient variables that are needed to track
    # the system's state (i.e. what trial number are we on and what is the next
    # parameter that needs to be presented) and are not needed once the
    # experiment is done.  A good rule of thumb: if the parameter is used as a
    # placeholder for transient data (to compute variables needed for experiment
    # control), it should be left out of the "model". 
    current_    = Any
    choice_     = Any

    # iface_* and buffer_* are handles to hardware needed to run the experiment.
    iface_      = Any
    buffer_     = Any

    data_       = Any
    pipeline_   = Any

    def init(self, info):
        log.debug("Initializing equipment")
        try:
            self.model = info.object
            log.debug("Initializing toolbars")
            for toolbar in self.trait_names(toolbar=True):
                getattr(self, toolbar).install(self, info)
            log.debug("Successfully initialized equipment")
        except Exception, e:
            log.error(e)
            self.state = 'disconnected'
            error(info.ui.control, str(e))

    def close(self, info, is_ok):
        '''
        Prevent user from closing window while an experiment is running since
        data is not saved to file until the stop button is pressed.
        '''
        if self.state not in ('disconnected', 'halted', 'complete'):
            mesg = 'Experiment is still running.  Are you sure you want to exit?'
            if confirm(info.ui.control, mesg) == YES:
                self.stop(info)
                return True
            else:
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
            self.start_experiment(info)
            self.model.start_time = datetime.now()
            self.timer_fast = Timer(100, self.tick_fast)
            self.timer_slow = Timer(500, self.tick_slow)
        except BaseException, e:
            log.exception(e)
            error(self.info.ui.control, str(e))

    def stop(self, info=None):
        try:
            self.timer_fast.Stop()
            self.timer_slow.Stop()
        except AttributeError:
            self.timer_fast.stop()
            self.timer_slow.stop()

        try:
            self.stop_experiment(info)
            self.model.stop_time = datetime.now()

            self.pending_changes = {}
            self.old_values = {}

            info.ui.view.close_result = True
            self.state = 'complete'
        except BaseException, e:
            log.exception(e)
            error(self.info.ui.control, str(e))

    ############################################################################
    # Apply/Revert code
    ############################################################################
    pending_changes     = Dict({})
    old_values          = Dict({})

    def init_paradigm(self, paradigm):
        '''
        Configuring the equipment based on initial values in the paradigm.  If
        the trait has the metadata flag, 'init', set to True, then the
        corresponding setter (set_trait_name) will be called with the initial
        value of the trait.
        '''
        for trait_name in paradigm.class_trait_names(init=True):
            value = getattr(paradigm, trait_name)
            getattr(self, 'set_' + trait_name)(value)

    @on_trait_change('model.paradigm.+')
    def queue_change(self, instance, name, old, new):
        if self.state <> 'halted':
            trait = self.model.paradigm.trait(name)
            if trait.immediate == True:
                print 'applying', name
                self.apply_change(instance, name, new)
            else:
                key = instance, name
                if key not in self.old_values:
                    self.old_values[key] = old
                    self.pending_changes[key] = new
                elif new == self.old_values[key]:
                    del self.pending_changes[key]
                    del self.old_values[key]
                else:
                    self.pending_changes[key] = new

    def apply_change(self, instance, name, value, info=None):
        '''
        Applies an individual change
        '''
        ts = self.get_ts()
        log.debug("Apply: setting %s:%s to %r", instance, name, value)
        try:
            getattr(self, 'set_'+name)(value)
            self.log_event(ts, name, value)
        except AttributeError:
            mesg = "Can't set %s to %r" % (name, value)
            # Notify the user
            error(info.ui.control, mesg)
            log.warn(mesg + ", removing from stack")
            # Set paradigm value back to "old" value
            setattr(self.model.paradigm, name, value)

    def apply(self, info=None):
        '''
        Called when Apply button is pressed.  Goes through all parameters that
        have changed and attempts to apply them.
        '''
        for key, value in self.pending_changes.items():
            instance, name = key
            self.apply_change(instance, name, value, info)
            del self.pending_changes[key]
            del self.old_values[key]

    def log_event(self, ts, name, value):
        log.debug("%d, %s, %r", ts, name, value)
        
    def revert(self, info=None):
        '''Revert changes requested while experiment is running.'''
        for (object, name), value in self.old_values.items():
            log.debug('reverting changes for %s', name)
            setattr(object, name, value)
        self.old_values = {}
        self.pending_changes = {}

    ############################################################################
    # Method stubs to be implemented
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

    def initialize_experiment(self, info=None):
        pass

    def init_current(self, info=None):
        '''
        Called whenever the trial sequence needs to be reset (e.g. the number of
        safes or the parameter sequence changes).
        '''
        raise NotImplementedException

    def start_experiment(self, info=None):
        '''
        Called when the experiment is started.  Initialize the equipment and
        buffers here.  Be sure to call init_current from this method at the
        appropriate point.
        '''
        raise NotImplementedException

    def stop_experiment(self, info=None):
        '''
        Called when the experiment is stopped.  Shut down any pieces of hardware
        needed and be sure to save your data!
        '''
        raise NotImplementedException

    def get_ts(self):
        raise NotImplementedException

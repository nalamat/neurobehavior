from copy import deepcopy, copy
from datetime import datetime, timedelta
from cns.data.persistence import add_or_update_object_node

from tdt import DSPProcess, DSPProject
from tdt.device import RZ6
from cns import get_config

from enthought.pyface.api import error, confirm, YES, ConfirmationDialog
from enthought.pyface.timer.api import Timer
from enthought.etsconfig.api import ETSConfig
from enthought.traits.api import (Any, Instance, Enum, Dict, on_trait_change, 
        HasTraits, List, Button, Bool, Tuple, Callable, Int, Property,
        cached_property, Undefined, Event, TraitError)
from enthought.traits.ui.api import Controller, View, HGroup, Item, spring

from cns.widgets.toolbar import ToolBar
from enthought.savage.traits.ui.svg_button import SVGButton
from cns.widgets import icons

from .physiology_controller_mixin import PhysiologyControllerMixin

from enthought.traits.api import HasTraits, Dict, on_trait_change, Property, \
        cached_property

from evaluate import evaluate_expressions, evaluate_value

from PyQt4 import QtGui

import logging
log = logging.getLogger(__name__)

class ExperimentToolBar(ToolBar):

    size    = 24, 24
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

class AbstractExperimentController(Controller, PhysiologyControllerMixin):
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
    current_    = Any(current=True)
    choice_     = Any(choice=True)

    # iface_* and buffer_* are handles to hardware and hardware memory buffers
    iface_      = Any(iface=True)
    buffer_     = Any(buffer=True)

    data_       = Any(data=True)
    pipeline_   = Any(pipeline=True)

    # List of tasks to be run during experiment.  Each entry is a tuple
    # (callable, frequency) where frequency is how often the task should be run.
    # Tasks that are slow (e.g. communciating with the pump) should not be run
    # as often.  A frequency of 1 indicates the task should be run on every
    # "tick" of the timer, a frequency of 5 indicates the task should be run
    # every 5 "ticks".  If the timer interval is set to 100 ms, then a frequency
    # of 5 corresponds to 500 ms.  However, be warned that this is not
    # deterministic.  If tasks take a while to complete, then the timer "slows
    # down" as a result.
    tasks       = List(Tuple(Callable, Int))
    tick_count  = Int(1)

    # The DSP process that will be responsible for handling all communication
    # with the DSPs.  All circuits must be loaded and buffers initialized before
    # the process is started (so the process can appropriately allocate the
    # required shared memory resources).
    process         = Any
    system_tray     = Any

    # Calibration objects
    cal_primary     = Instance('neurogen.Calibration')
    cal_secondary   = Instance('neurogen.Calibration')

    def init(self, info):
        try:
            self.model = info.object

            # The toolbars need a reference to the handler (i.e. this class) so
            # they can communicate button-presses.
            for toolbar in self.trait_names(toolbar=True):
                getattr(self, toolbar).install(self, info)

            # If we want to spool physiology, launch the physiology window as
            # well.  It should appear in the second monitor.  The parent of this
            # window should be the current window (info.ui.control) that way
            # both windows get closed when the app exits.
            if self.model.spool_physiology:
                self.window_physiology = info.object.edit_traits(
                        parent=self.window_behavior,
                        view='physiology_view').control

        except Exception, e:
            log.exception(e)
            self.state = 'disconnected'
            error(info.ui.control, str(e))

        # Use this for non-blocking error messages
        self.system_tray = QtGui.QSystemTrayIcon(info.ui.control)
        self.system_tray.messageClicked.connect(self.message_clicked)
        self.system_tray.setVisible(True)
        
    def close(self, info, is_ok):
        '''
        Prevent user from closing window while an experiment is running since
        data is not saved to file until the stop button is pressed.
        '''

        # We can abort a close event by returning False.  If an experiment
        # is currently running, confirm that the user really did want to close
        # the window.  If no experiment is running, then it's OK since the user
        # can always restart the experiment.
        if self.state not in ('disconnected', 'halted', 'complete'):
            mesg = 'Experiment is still running.  Are you sure you want to exit?'

            # The function confirm returns an integer that represents the
            # response that the user requested.  YES is a constant (also
            # imported from the same module as confirm) corresponding to the
            # return value of confirm when the user presses the "yes" button on
            # the dialog.  If any other button (e.g. "no", "abort", etc.) is
            # pressed, the return value will be something other than YES and we
            # will assume that the user has requested not to quit the
            # experiment.
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
        try:
            if get_config('RCX_USE_SUBPROCESS'):
                log.debug("USING DSP PROCESS")
                self.process = DSPProcess()
            else:
                log.debug("USING DSP PROJECT")
                self.process = DSPProject()
            # I don't really like having this check here; however, it works
            # for our purposes.
            if self.model.spool_physiology:
                # Ensure that the settings are applied
                self.setup_physiology()

            # setup_experiment should load the necessary circuits and
            # initialize the buffers. This data is required before the
            # hardware process is launched since the shared memory, locks and
            # pipelines must be created.
            self.setup_experiment(info)

            # Start the harware process
            self.process.start()

            if self.model.spool_physiology:
                settings = self.model.physiology_settings
                self.init_paradigm(settings)
                settings.on_trait_change(self.queue_change, '+')
                self.tasks.append((self.monitor_physiology, 1))

            # Now that the process is started, we can configure the circuit
            # (e.g. read/write to tags) and gather the information we need to
            # run the experiment.
            self.start_experiment(info)

            # Save the start time in the model
            self.model.start_time = datetime.now()
            self.timer = Timer(100, self.run_tasks)

        except Exception, e:
            log.exception(e)
            error(self.info.ui.control, str(e))

    def stop(self, info=None):
        try:
            self.timer.stop()
            self.process.stop()
            self.pending_changes = {}
            self.old_values = {}
        except Exception, e:
            log.exception(e)
            error(self.info.ui.control, str(e))

        try:
            self.stop_experiment(info)
            self.model.stop_time = datetime.now()
            info.ui.view.close_result = True
            self.state = 'complete'
        except Exception, e:
            log.exception(e)
            error(self.info.ui.control, str(e))
        finally:
            # Always attempt to save, no matter what!
            add_or_update_object_node(self.model, self.model.exp_node)
            
    def run_tasks(self):
        for task, frequency in self.tasks:
            if frequency == 1 or not (self.tick_count % frequency):
                try:
                    task()
                except Exception, e:
                    # Display an error message to the user
                    log.exception(e)
                    mesg = "The following exception occured in the program:" + \
                            "\n\n%s"
                    mesg = mesg % str(e)
                    self.system_tray.showMessage("Error running task", mesg)
        self.tick_count += 1

    def message_clicked(self):
        mesg = "An exception occured in the program.  What should we do?"
        dialog = ConfirmationDialog(message=mesg, yes_label='Stop',
                no_label='Continue')
        if dialog.open() == YES:
            self.stop(self.info)

    ############################################################################
    # Method stubs to be implemented
    ############################################################################
    
    def resume(self, info=None):
        raise NotImplementedError

    def pause(self, info=None):
        raise NotImplementedError

    def remind(self, info=None):
        raise NotImplementedError

    def initialize_experiment(self, info=None):
        raise NotImplementedError

    def start_experiment(self, info=None):
        '''
        Called when the experiment is started.  Initialize the equipment and
        buffers here.  Be sure to call init_current from this method at the
        appropriate point.
        '''
        raise NotImplementedError

    def stop_experiment(self, info=None):
        '''
        Called when the experiment is stopped. This can normally be (safely)
        left unimplemented.
        '''
        pass

    def get_ts(self):
        '''
        Return the current timestamp. Should be a value that we can reference
        against the rest of the data we are collecting in the experiment.
        '''
        raise NotImplementedError

    def set_speaker_mode(self, value):
        self.current_speaker_mode = value

    def set_attenuations(self, att1, att2):
        # TDT's built-in attenuators for the RZ6 function in 20 dB steps, so we
        # need to determine the next greater step size for the attenuator.  The
        # maximun hardware attenuation is 60 dB.
        hw1, sw1 = RZ6.split_attenuation(att1)
        hw2, sw2 = RZ6.split_attenuation(att2)

        # Don't update unless either has changed!
        if (hw1 != self.current_hw_att1) or (hw2 != self.current_hw_att2):
            #self.iface_behavior.set_att_bits(RZ6.atten_to_bits(hw1, hw2))
            self.iface_behavior.set_tag('att1', hw1)
            self.iface_behavior.set_tag('att2', hw2)
            self.output_primary.hw_attenuation = hw1
            self.output_primary.hw_attenuation = hw2
            self.current_hw_att1 = hw1
            self.current_hw_att2 = hw2
            log.debug('Set hardware attenuation to %.2f and %.2f', hw1, hw2)

    def set_expected_speaker_range(self, value):
        self._update_attenuators()

    def set_fixed_attenuation(self, value):
        self._update_attenuators()

    def set_speaker_equalize(self, value):
        self.output_primary.equalize = value
        self.output_secondary.equalize = value

    def _update_attenuators(self):
        if self.get_current_value('fixed_attenuation'):
            expected_range = self.get_current_value('expected_speaker_range')
            expected_range = [(s.frequency, s.max_level) for s in expected_range]
            att1 = self.cal_primary.get_best_attenuation(expected_range)
            att2 = self.cal_secondary.get_best_attenuation(expected_range)
            log.debug('Best attenuations are %.2f and %.2f', att1, att2)
            self.set_attenuations(att1, att2)
        else:
            self.output_primary.hw_attenuation = None
            self.output_secondary.hw_attenuation = None

    def log_trial(self, **kwargs):
        for key, value in self.context_log.items():
            if value:
                kwargs[key] = self.current_context[key]
        self.model.data.log_trial(**kwargs)

    def log_event(self, ts, name, value):
        self.model.data.log_event(ts, name, value)
        log.debug("EVENT: %d, %s, %r", ts, name, value)

    '''
    If an experiment is running, we need to queue changes to most of the
    settings in the GUI to ensure that the user has a chance to finish making
    all the changes they desire before the new settings take effect.
    
    Supported metadata
    ------------------
    ignore
        Do not monitor the trait for changes
    immediate
        Apply the changes immediately (i.e. do not queue the changes)
        
    Handling changes to a parameter
    -------------------------------
    When a parameter is modified via the GUI, the controller needs to know how
    to handle this change.  For example, changing the pump rate or reward
    volume requires sending a command to the pump via the serial port.
    
    When a change to a parameter is applied, the class instance the parameter
    belongs to is checked to see if it has a method, "set_parameter_name",
    defined. If not, the controller checks to see if it has the method defined
    on itself.
    
    The function must have the following signature
    
    def set_parameter_name(self, value)
    '''

    pending_changes = Dict
    old_values = Dict

    @classmethod
    def _get_context_name(cls, instance, trait):
        '''
        Return a name that can be accessed via the context namespace.
        '''
        value = getattr(instance, trait)
        if getattr(instance, 'namespace', None) is not None:
            return '{}.{}'.format(instance.namespace, trait)
        return trait
    
    #@on_trait_change('model.[data,paradigm].+container*.[+context, +monitor]')
    @on_trait_change('model.[data,paradigm].[+context, +monitor]',
                     'model.[data,paradigm].+container.[+context, +monitor]')
    def handle_change(self, instance, name, old, new):
        '''
        Handles changes to traits in the paradigm that have the monitor
        attribute set to True.  This will also handle traits on objects in the
        paradigm provided you set the object's metadata to container.
        '''
        if self.state <> 'halted':
            # Obtain the trait definition so we can query its metadata
            trait = instance.trait(name)
            if name.endswith('_items'):
                # Trait change notifications to list items require special
                # handling. For simplicity, let's just rebuild the old and new
                # values of the list and treat the change as a completely new
                # list.
                removed, added = new.removed, new.added
                name = name[:-6] # strip the '_items' part
                new = getattr(instance, name)[:]
                old = new[:]

                for e in removed:
                    old.append(e)
                for e in added:
                    old.remove(e)
                
            if trait.immediate:
                self.current_expressions[name] = new
                self.pending_expressions[name] = new
                self.evaluate_pending_expressions()
            else:
                self.queue_change(instance, name, old, new)
                
    def queue_change(self, instance, name, old, new):
        '''
        Queue a change and make a backup of its old value so we can revert if
        desired.
        '''
        key = instance, name

        if key not in self.old_values:
            # This is the first time a change has been requested to the trait.
            # Cache the old value and add the trait to the dictionary of changes
            # that need to be applied.
            self.old_values[key] = old
            self.pending_changes[key] = new
        elif new == self.old_values[key]:
            # The user set the value back to its original value without
            # explicitly requesting a revert.  Remove the trait from the stack
            # since it no longer needs to be applied.
            del self.pending_changes[key]
            del self.old_values[key]
        else:
            # There is currently a pending change for the trait in the system,
            # but a new value has been requested.  Update the dictionary of
            # requested changes with the most recently requested value.  Do not
            # update the cache of old values since this cache is meant to
            # reflect the value of the trait the last time the apply() function
            # was called.
            self.pending_changes[key] = new

    def apply(self, info=None):
        '''
        Apply all pending changes.
        '''
        # Make a backup of the pending changes just in case something happens so
        # we can roll back to the original values.
        pending_changes_backup = self.pending_changes.copy()
        old_values_backup = self.old_values.copy()
        current_expressions_backup = self.current_expressions.copy()
        
        try:
            # Attempt to evaluate the expressions and apply the resulting values
            for (instance, name), value in self.pending_changes.items():
                xname = self._get_context_name(instance, name)
                self.current_expressions[xname] = deepcopy(value)
                del self.pending_changes[instance, name]
                del self.old_values[instance, name]
            self.invalidate_context()
            self.evaluate_pending_expressions()
        except Exception, e:
            # A problem occured when attempting to apply the context. Roll back
            # the changes and notify the user.  Hopefully we never reach this
            # point.
            self.apply_context(self.old_context)
            self.pending_changes = pending_changes_backup
            self.old_values = old_values_backup
            self.current_expressions = current_expressions_backup
            self.pending_expressions = {}

            log.exception(e)
            mesg = '''Unable to apply your requested changes due to an error. No
            changes have been made. Please review the changes you have requested
            to ensure that they are indeed valid.\n\n''' + str(e)
            error(info.ui.control, message=mesg, title='Error applying changes')

    def revert(self, info=None):
        '''
        Revert GUI fields to original values
        '''
        for (instance, name), value in self.old_values.items():
            try:
                setattr(instance, name, value)
            except TraitError, e:
                # This is raised for readonly traits so we'll pass them by
                print e
                pass
        self.old_values = {}
        self.pending_changes = {}
    
    current_expressions = Dict
    pending_expressions = Dict
    current_evaluated = Dict
    current_context = Dict
    context_labels = Dict
    context_log = Dict
    old_context = Dict

    current_context_updated = Event

    # List of name, value, label tuples (used for displaying in the GUI)
    current_context_list = List

    def invalidate_context(self):
        '''
        Invalidate the current context.  This forces the program to reevaluate
        all expressions.
        '''
        self.old_context = self.current_context.copy()
        self.pending_expressions = self.current_expressions.copy()
        self.current_context = {}

    def get_current_value(self, name):
        '''
        Get the current value of a context variable.  If the context variable
        has not been evaluated yet, compute its value from the
        pending_expressions stack.  Additional context variables may be
        evaluated as needed.
        '''
        try:
            return self.current_context[name]
        except:
            evaluate_value(name, self.pending_expressions, self.current_context)
            self.current_context_updated = True
            return self.current_context[name]

    def evaluate_pending_expressions(self, extra_context=None):
        '''
        Evaluate all pending expressions and store results in current_context.

        If extra_content is provided, it will be included in the local
        namespace. If extra_content defines the value of a parameter also
        present in pending_expressions, the value stored in extra_context takes
        precedence.
        '''
        if extra_context is not None:
            self.current_context.update(extra_context)
            for key in extra_context:
                if key in self.pending_expressions:
                    del self.pending_expressions[key]
        evaluate_expressions(self.pending_expressions, self.current_context)
        self.current_context_updated = True

    def apply_context(self, context):
        for name, value in context.items():
            self._apply_context_value(name, value)
        self.current_context_updated = True

    @on_trait_change('current_context_items')
    def _apply_context_changes(self, event):
        '''
        Automatically apply changes as expressions are evaluated and their
        result added to the context
        '''
        for name, value in event.added.items():
            if self.old_context.get(name, None) != value:
                self._apply_context_value(name, value)
        for name, value in event.changed.items():
            if self.old_context.get(name, None) != value:
                self._apply_context_value(name, value)

    def _apply_context_value(self, name, value):
        log.debug('Applying %s', name)
        try:
            getattr(self, 'set_{}'.format(name))(value)
        except AttributeError, e:
            log.warn(str(e))

    @on_trait_change('current_context_updated')
    def _update_current_context_list(self):
        context = []
        for name, value in self.current_context.items():
            label = self.context_labels.get(name, '')
            changed = not self.old_context.get(name, None) == value
            log = self.context_log[name]
            context.append((name, value, label, log, changed))
        self.current_context_list = sorted(context)

    def populate_context(self, instance):
        '''
        Identify all traits that should be part of the context to be evaluated
        and add them to the current expression dictionary.
        '''
        for name, trait in instance.traits(context=True).items():
            xname = self._get_context_name(instance, name)
            self.current_expressions[xname] = getattr(instance, name)
            self.context_labels[xname] = trait.label
            self.context_log[xname] = trait.log
        self.pending_expressions = self.current_expressions.copy()

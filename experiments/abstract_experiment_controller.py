from datetime import datetime
from cns.data.h5_utils import get_or_append_node

# Enthought supports both the PySide and Qt4 backend.  PySide is
# essentially a rewrite of PyQt4.  These backends are not compatible
# with each other, so we need to be sure to import the backend that
# Enthought has decided to use.
from pyface.qt import QtGui

import subprocess
from os import path
import platform

from .evaluate import evaluate_value, evaluate_expressions

from cns import get_config

from pyface.api import error, confirm, YES
from pyface.timer.api import Timer
from traits.api import (Any, Instance, Enum, Dict, List, Bool, Tuple,
                                  Callable, Int, Property, Event, Str, Float,
                                  Trait, on_trait_change)
from traitsui.api import Controller, View, HGroup, Item, spring

from cns.widgets.toolbar import ToolBar
from enable.savage.trait_defs.ui.svg_button import SVGButton
from cns.widgets.icons import icons

import logging
log = logging.getLogger(__name__)

from .utils import load_instance, dump_instance

from physiology_experiment import PhysiologyExperiment
from physiology_data import PhysiologyData
from physiology_controller import PhysiologyController

DATETIME_FMT = get_config('DATETIME_FMT')
DATE_FMT = get_config('DATE_FMT')

class ExperimentToolBar(ToolBar):

    size    = 24, 24
    kw      = dict(height=size[0], width=size[1], action=True)
    apply   = SVGButton('Apply', filename=icons['apply'],
                        tooltip='Apply settings', **kw)
    revert  = SVGButton('Revert', filename=icons['undo'],
                        tooltip='Revert settings', **kw)
    start   = SVGButton('Run', filename=icons['start'],
                        tooltip='Begin experiment', **kw)
    pause   = SVGButton('Pause', filename=icons['pause'],
                        tooltip='Pause', **kw)
    resume  = SVGButton('Resume', filename=icons['resume'],
                        tooltip='Resume', **kw)
    stop    = SVGButton('Stop', filename=icons['stop'],
                        tooltip='stop', **kw)
    remind  = SVGButton('Remind', filename=icons['warn'],
                        tooltip='Remind', **kw)
    cancel_remind = SVGButton('Cancel Remind', filename=icons['warn'],
            tooltip='Remind', **kw)
    item_kw = dict(show_label=False)

    traits_view = View(
            HGroup(Item('apply',
                        enabled_when="object.handler.pending_changes",
                        **item_kw),
                   Item('revert',
                        enabled_when="object.handler.pending_changes",
                        **item_kw),
                   Item('start',
                        enabled_when="object.handler.state=='halted'",
                        **item_kw),
                   '_',
                   Item('remind',
                        enabled_when="object.handler.state=='running' and not object.handler.remind_requested",
                        **item_kw),
                #    Item('cancel_remind',
                #         enabled_when="object.handler.state=='running' and object.handler.remind_requested",
                #         **item_kw),
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
    """
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
    """
    shell_variables = Dict

    # These define what variables will be available in the Python shell.  Right
    # now we can't add various stuff such as the data and interface classes
    # because they have not been created yet.  I'm not sure how we can update
    # the Python shell with new instances once the experiment has started
    # running.
    def _shell_variables_default(self):
        return dict(controller=self, c=self)

    # If you add a toolbar, be sure to set toolbar=True so that the controller
    # knows that the toolbar instance needs to be "installed".
    toolbar = Instance(ExperimentToolBar, (), toolbar=True)

    state = Enum('halted', 'paused', 'running', 'manual', 'disconnected',
                 'complete')

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

    system_tray     = Any

    # Calibration objects
    cal_primary     = Instance('cns.calibration.Calibration')
    cal_secondary   = Instance('cns.calibration.Calibration')

    physiology_handler = Instance(PhysiologyController)

    status = Property(Str, depends_on='trial_state, current_setting')

    # Start time of the experiment, in seconds
    start_time = Any

    def _get_status(self):
        if self.state == 'disconnected':
            return 'Error'
        elif self.state == 'halted':
            return 'Halted'
        elif self.current_setting is not None:
            return str(self.current_setting)
        else:
            return ''

    def handle_error(self, error):
        # Since this is a critical error, we should force the window to the top
        # so the user knows there is a problem. Typically this is considered
        # rude behavior in programming; however, experiments take priority.
        mesg = '{}\n\nDo you wish to stop the program?'.format(error)
        self.info.ui.control.activateWindow()
        if confirm(self.info.ui.control, mesg, 'Error while running') == YES:
            self.stop(self.info)

    def notify(self, message):
        self.system_tray.showMessage('Neurobehavior notification', message)

    def init(self, info):
        try:
            self.model = info.object

            # The toolbars need a reference to the handler (i.e. this class) so
            # they can communicate button-presses to the controller.
            for toolbar in self.trait_names(toolbar=True):
                getattr(self, toolbar).install(self, info)

            # If we want to spool physiology, launch the physiology window as
            # well.  It should appear in the second monitor.  The parent of this
            # window should be the current window (info.ui.control) that way
            # both windows get closed when the app exits.
            if self.model.spool_physiology:
                data_node = info.object.data_node
                node = get_or_append_node(data_node, 'physiology')
                data = PhysiologyData(store_node=node)
                experiment = PhysiologyExperiment(data=data, parent=info.object)
                # handler = PhysiologyController(process=self.process,
                #                                parent=self, state='client')
                handler = PhysiologyController(parent=self, state='client')
                experiment.edit_traits(handler=handler, parent=None)
                self.physiology_handler = handler

            # Create a system tray for notification messages.  Using popups do
            # not seem to work very well.  Either the popups are modal (in which
            # case they block the program from continuing to run) or they
            # dissappear below the main window.  I really don't like this
            # approach, but I can't think of a better way to do it ...
            icon_path = path.join(path.dirname(__file__), 'psi_uppercase.svg')
            icon = QtGui.QIcon(icon_path)
            self.system_tray = QtGui.QSystemTrayIcon()
            self.system_tray.setIcon(icon)
            #self.system_tray.setVisible(True)
        except Exception, e:
            log.exception(e)
            self.state = 'disconnected'
            error(info.ui.control, str(e))

    def close(self, info, is_ok):
        '''
        Prevent user from closing window while an experiment is running since
        data is not saved to file until the stop button is pressed.
        '''
        # We can abort a close event by returning False.  If an experiment
        # is currently running, confirm that the user really did want to close
        # the window.  If no experiment is running, then it's OK since the user
        # can always restart the experiment.
        close = True
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
            if confirm(info.ui.control, mesg) != YES:
                close = False
            else:
                self.stop(info)

        if close:
            pass
            #if self.physiology_handler is not None:
                #print 'attemting to close handler'
                #self.physiology_handler.close(info, True, True)
        return close

    def start(self, info=None):
        '''
        Handles starting an experiment (called when the start button is pressed)

        Subclasses must implement `start_experiment`
        '''
        if self.state != 'halted':
            # Don't attempt to start experiment, it is already running or has
            # stopped.
            return
        try:
            node = info.object.experiment_node

            # Get the current revision of the program code so that we can
            # properly determine the version used to run the code.  I'm not sure
            # what happens if Hg is not installed on the computer.  However, we
            # currently don't have to deal with that use-case.
            try:
                dir = path.abspath(path.dirname(__file__))
                rev_id = subprocess.check_output('hg id --cwd {}'.format(dir))
                node._v_attrs['neurobehavior_revision'] = rev_id
            except:
                import warnings
                mesg = "Unable to store changset ID of Neurobehavior"
                warnings.warn(mesg)
                self.notify(mesg)

            # Store the value of all the settings when the experiment was
            # launched
            for k, v in get_config().items():
                node._v_attrs['setting_' + k] = v

            # Get the computer host name so we know which computer was used
            node._v_attrs['computer'] = platform.uname()[1]

            # This will actually store a pickled copy of the calibration data
            # that can *only* be recovered with Python (and a copy of the
            # Neurobehavior module)
            node._v_attrs['cal_1'] = self.cal_primary
            node._v_attrs['cal_2'] = self.cal_secondary

            self.start_time = datetime.now()
            node._v_attrs['start_time'] = self.start_time.strftime(DATETIME_FMT)
            node._v_attrs['date'] = self.start_time.strftime(DATE_FMT)

            # setup_experiment should load the necessary circuits and initialize
            # the buffers. This data is required before the hardware process is
            # launched since the shared memory, locks and pipelines must be
            # created.
            self.setup_experiment(info)

            # Sorta a hack
            if self.model.spool_physiology:
                self.physiology_handler.start()

            # Now that the process is started, we can configure the circuit
            # (e.g. read/write to tags) and gather the information we need to
            # run the experiment.
            self.initialize_context()
            self.start_experiment(info)

            # Save the start time in the model
            self.model.start_time = datetime.now()
        except Exception, e:
            if self.state != 'halted':
                self.stop_experiment(info)
            log.exception(e)
            mesg = '''
            Unable to start the experiment due to an error.  Please correct the
            error condition and attempt to restart the experiment.  Note that
            you may have to shut down and start the program again.
            '''
            import textwrap
            mesg = textwrap.dedent(mesg).strip().replace('\n', ' ')
            mesg += '\n\nError message: ' + str(e)
            error(self.info.ui.control, mesg, title='Error starting experiment')

    def stop(self, info=None):
        try:
            self.pending_changes = False
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
            # Always attempt to save the data, no matter what happens!
            node = info.object.experiment_node
            time = datetime.now()
            node._v_attrs['stop_time'] = time.strftime(DATETIME_FMT)
            node._v_attrs['duration'] = (time-self.start_time).seconds
            info.object.data.save()

    ############################################################################
    # Method stubs to be implemented
    ############################################################################

    def resume(self, info=None):
        raise NotImplementedError

    def pause(self, info=None):
        raise NotImplementedError

    def remind(self, info=None):
        raise NotImplementedError

    def setup_experiment(self, info=None):
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

    def log_trial(self, **kwargs):
        '''
        Add entry to trial log table

        In addition to the data provided via kwargs, the current value of all
        parameters for that given trial will be included.  The keys of the
        kwargs dictionary will be used as the column names.

        The first call to log_trial establishes the columns that will be present
        on every call.  Subsequent calls to log_trial must use the exact same
        set of keys (e.g. you cannot remove or add new parameters on each call).

        This is a valid sequence of calls:

            self.log_trial(hw_atten=120, noise_seed=4)
            ...
            self.log_trial(hw_atten=20, noise_seed=5)
            ...
            self.log_trial(hw_atten=30, noise_seed=6)
            ...

        This is an invalid sequence of calls:

            self.log_trial(hw_atten=120, noise_seed=4)
            ...

            # Invalid because a keyword argument provided in the first call is
            # missing
            self.log_trial(noise_seed=5)
            ...

            # Invalid because a keyword argument not provided in the first call
            # has been added
            self.log_trial(hw_atten=30, noise_seed=6, noise_bandwidth=1000)
            ...

        '''
        for key, value in self.context_log.items():
            if value:
                kwargs[key] = self.current_context[key]
        for key, value in self.shadow_paradigm.trait_get(context=True).items():
            kwargs['expression_{}'.format(key)] = '{}'.format(value)
        self.model.data.log_trial(**kwargs)

    def log_event(self, ts, event):
        self.model.data.log_event(ts, event)
        log.debug("EVENT: %d, %s, %r", ts, name, message)

    # Simplest way to load/save paradigms is via Python's pickle module which
    # persists the object data to a binary file on disk.  Note that this file
    # format is specific to Python's pickle module and will not be
    # human-readable (or Matlab readable unless you want to write the
    # appropriate converter).

    def load_paradigm(self, info):
        try:
            PARADIGM_ROOT = get_config('PARADIGM_ROOT')
            PARADIGM_WILDCARD = get_config('PARADIGM_WILDCARD')
            instance = load_instance(PARADIGM_ROOT, PARADIGM_WILDCARD)
            if instance is not None:
                self.model.paradigm.copy_traits(instance)
        except AttributeError, e:
            log.exception(e)
            mesg = '''
            Unable to load paradigm.  This can be due to 1) the
            paradigm saved in the file being incompatible with the version
            currently running or 2) the paradigm was saved with an older version
            of Python's pickle module.'''
            import textwrap
            mesg = textwrap.dedent(mesg).replace('\n', ' ').strip()
            error(self.info.ui.control, mesg)

    def saveas_paradigm(self, info):
        PARADIGM_ROOT = get_config('PARADIGM_ROOT')
        PARADIGM_WILDCARD = get_config('PARADIGM_WILDCARD')
        dump_instance(self.model.paradigm, PARADIGM_ROOT, PARADIGM_WILDCARD)

    calibration_window = Any

    def show_calibration(self, info):
        # TODO: add logic to bring calibration window back to front if the user
        # calls this function again rather than generating a second popup
        if self.calibration_window is None:
            from calibration_plot import CalibrationPlot
            calibrations = [self.cal_primary, self.cal_secondary]
            self.calibration_window = CalibrationPlot(calibrations=calibrations)
        self.calibration_window.edit_traits()

    '''
    APPLY/REVERT ATTRIBUTES AND LOGIC

    If an experiment is running, we need to queue changes to most of the
    settings in the GUI to ensure that the user has a chance to finish making
    all the changes they desire before the new settings take effect.

    Supported metadata
    ------------------
    context
        Include in the context namespace.  Note that for a Trait to be logged,
        it must also be
    immediate
        Apply the changes immediately (i.e. do not queue the changes)

    Handling changes to a parameter
    -------------------------------
    When a parameter is modified via the GUI, the controller needs to know how
    to handle this change.  For example, changing the pump rate or reward volume
    requires sending a command to the pump via the serial port.

    When a change to a parameter is applied, the class instance the parameter
    belongs to is checked to see if it has a method, "set_parameter_name",
    defined. If not, the controller checks to see if it has the method defined
    on itself.

    The function must have the following signature set_parameter_name(self,
    value)

    '''

    # Boolean flag indicating whether there are any changes to paradigm
    # variables that have not been applied.  Currently the apply/revert logic is
    # not smart enough to handle cases where the user makes a sequence of
    # changes that results in the final value being equivalent to the original
    # value.
    pending_changes = Bool(False)

    # A shadow copy of the paradigm where the current values used for the
    # experiment are stored.  The copy of the paradigm at info.object.paradigm
    # is a separate copy that is currently being edited via the GUI.
    shadow_paradigm = Any

    # List of expressions that have not yet been evaluated.
    pending_expressions = Dict

    # The current value of all context variables
    current_context = Dict

    # Label of the corresponding variable to use in the GUI
    context_labels = Dict

    # Should the context variable be logged?
    context_log = Dict

    # Copy of the old context (used for comparing with the current context to
    # determine if a value has changed)
    old_context = Dict

    # List of name, value, label tuples (used for displaying in the GUI)
    current_context_list = List

    @on_trait_change('model.paradigm.+container*.+context, +context')
    def handle_change(self, instance, name, old, new):
        # When a paradigm value has changed while the experiment is running,
        # indicate that changes are pending
        if self.state == 'halted':
            return

        log.debug('Detected change to %s', name)

        trait = instance.trait(name)
        if trait.immediate:
            self.set_current_value(name, new)
        else:
            self.pending_changes = True

    def invalidate_context(self):
        '''
        Invalidate the current context.  This forces the program to reevaluate
        any values that may have changed.
        '''
        import warnings
        warnings.warn('Method has been replaced by refresh_context')
        self.refresh_context()

    def refresh_context(self):
        '''
        Stores a copy of self.current_context in self.old_context, wipes
        self.current_context, and reloads the expressions from the paradigm.
        '''
        log.debug('Refreshing context')
        self.old_context = self.current_context.copy()
        self.current_context = self.trait_get(context=True)
        self.current_context.update(self.model.data.trait_get(context=True))
        self.pending_expressions = self.shadow_paradigm.trait_get(context=True)

    def apply(self, info=None):
        '''
        This method is called when the apply button is pressed
        '''
        log.debug('Applying requested changes')
        try:
            # First, we do a quick check to ensure the validity of the
            # expressions the user entered by evaluating them.  If the
            # evaluation passes, we will make the assumption that the
            # expressiosn are valid as entered.  However, this will *not* catch
            # all edge cases or situations where actually applying the change
            # causes an error.
            pending_expressions = self.model.paradigm.trait_get(context=True)
            current_context = self.model.data.trait_get(context=True)
            evaluate_expressions(pending_expressions, current_context)

            # If we've made it this far, then let's go ahead and copy the
            # changes over to our shadow_paradigm.  We'll apply the requested
            # changes immediately if a trial is not currently running.
            self.shadow_paradigm.copy_traits(self.model.paradigm)
            self.pending_changes = False

            # Subclasses need to define this function (e.g.
            # abstract_positive_controller and abstract_aversive_controller)
            # because only those subclases know when it's safe to apply the
            # changes (e.g. the positive paradigms will check to make sure that
            # a trial is not running before applying the changes).
            self.context_updated()
        except Exception, e:
            # A problem occured when attempting to apply the context.
            # the changes and notify the user.  Hopefully we never reach this
            # point.
            log.exception(e)
            mesg = '''
            Unable to apply your requested changes due to an error.  No changes
            have been made. Please review the changes you have requested to
            ensure that they are indeed valid.'''
            import textwrap
            mesg = textwrap.dedent(mesg).strip().replace('\n', ' ')
            mesg += '\n\nError message: ' + str(e)
            error(info.ui.control, message=mesg, title='Error applying changes')

    def context_updated(self):
        '''
        This can be overriden in subclasses to implement logic for updating the
        experiment when the apply button is pressed
        '''
        pass

    def revert(self, info=None):
        '''
        Revert GUI fields to original values
        '''
        log.debug('Reverting requested changes')
        self.model.paradigm.copy_traits(self.shadow_paradigm)
        self.pending_changes = False

    def value_changed(self, name):
        new_value = self.get_current_value(name)
        old_value = self.old_context.get(name, None)
        return new_value != old_value

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
            return self.current_context[name]

    get_value = get_current_value

    def set_current_value(self, name, value):
        self.current_context[name] = value

    def evaluate_pending_expressions(self, extra_context=None):
        '''
        Evaluate all pending expressions and store results in current_context.

        If extra_content is provided, it will be included in the local
        namespace. If extra_content defines the value of a parameter also
        present in pending_expressions, the value stored in extra_context takes
        precedence.
        '''
        log.debug('Evaluating pending expressions')
        if extra_context is not None:
            self.current_context.update(extra_context)
        self.current_context.update(self.model.data.trait_get(context=True))
        evaluate_expressions(self.pending_expressions, self.current_context)

    @on_trait_change('current_context_items')
    def _apply_context_changes(self, event):
        '''
        Automatically apply changes as expressions are evaluated and their
        result added to the context
        '''
        names = event.added.keys()
        names.extend(event.changed.keys())
        for name in names:
            old_value = self.old_context.get(name, None)
            new_value = self.current_context.get(name)
            if old_value != new_value:
                mesg = 'changed {} from {} to {}'
                log.debug(mesg.format(name, old_value, new_value))

                # I used to have this in a try/except block (i.e. using the
                # Python idiom of "it's better to ask for forgiveness than
                # permission).  However, it quickly became apparent that this
                # was masking Exceptions that may be raised in the body of the
                # setter functions.  We should let these exceptions bubble to
                # the surface so the user has more information about what
                # happened.
                setter = 'set_{}'.format(name)
                if hasattr(self, setter):
                    getattr(self, setter)(new_value)
                    log.debug('setting %s', name)
                else:
                    log.debug('no setter for %s', name)

    @on_trait_change('current_context_items')
    def _update_current_context_list(self):
        context = []
        for name, value in self.current_context.items():
            label = self.context_labels.get(name, '')
            changed = not self.old_context.get(name, None) == value
            log = self.context_log[name]
            if type(value) in ((type([]), type(()))):
                str_value = ', '.join('{}'.format(v) for v in value)
                str_value = '[{}]'.format(str_value)
            else:
                str_value = '{}'.format(value)
            context.append((name, str_value, label, log, changed))
        self.current_context_list = sorted(context)

    def initialize_context(self):
        log.debug('Initializing context')
        for instance in (self.model.data, self.model.paradigm, self):
            for name, trait in instance.traits(context=True).items():
                log.debug('Found context variable {}'.format(name))
                self.context_labels[name] = trait.label
                self.context_log[name] = trait.log

        # TODO: this is sort of a "hack" to ensure that the appropriate data for
        # the trial type is included
        #self.context_labels['ttype'] = 'Trial type'
        #self.context_log['ttype'] = True
        self.shadow_paradigm = self.model.paradigm.clone_traits()
        self.refresh_context()

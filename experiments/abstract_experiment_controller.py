from copy import deepcopy, copy
from datetime import datetime, timedelta
from cns.data.persistence import add_or_update_object_node

from tdt import DSPProject
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

from .apply_revert_controller_mixin import ApplyRevertControllerMixin

from PyQt4 import QtGui

import logging
log = logging.getLogger(__name__)

from enthought.pyface.api import FileDialog, OK
from cns import get_config

def get_save_file(path, wildcard):
    wildcard = wildcard.split('|')[1][1:]
    fd = FileDialog(action='save as', default_directory=path, wildcard=wildcard)
    if fd.open() == OK and fd.path <> '':
        if not fd.path.endswith(wildcard):
            fd.path += wildcard
        return fd.path
    return None

def load_instance(path, wildcard):
    fd = FileDialog(action='open', default_directory=path, wildcard=wildcard)
    if fd.open() == OK and fd.path <> '':
        import cPickle as pickle
        with open(fd.path, 'rb') as infile:
            return pickle.load(infile)
    else:
        return None

def dump_instance(instance, path, wildcard):
    filename = get_save_file(path, wildcard)
    if filename is not None:
        import cPickle as pickle
        with open(filename, 'wb') as outfile:
            pickle.dump(instance, outfile)
        return True
    return False

PARADIGM_ROOT = get_config('PARADIGM_ROOT')
PARADIGM_WILDCARD = get_config('PARADIGM_WILDCARD')


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

class AbstractExperimentController(PhysiologyControllerMixin,
                                   ApplyRevertControllerMixin, Controller):
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
    process         = Instance(DSPProject, ())
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
                info.object.edit_traits(view='physiology_view').control

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

    shadow_ = Any

    def start(self, info=None):
        '''
        Handles starting an experiment

        Subclasses must implement `start_experiment`
        '''
        try:
            # I don't really like having this check here; however, it works for
            # our purposes.
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

    def load_paradigm(self, info):
        instance = load_instance(PARADIGM_ROOT, PARADIGM_WILDCARD)
        if instance is not None:
            self.model.paradigm = instance

    def saveas_paradigm(self, info):
        dump_instance(self.model.paradigm, PARADIGM_ROOT, PARADIGM_WILDCARD)

    #def select_parameters(self, info):
    #    parameters = self.model.paradigm.get_parameter_info().keys()
    #    print ParameterSelector(available_parameters=parameters).edit_traits().parameters

#from enthought.traits.ui.api import SetEditor
#
#class ParameterSelector(HasTraits):
#
#    EDITOR = SetEditor(name='available_parameters')
#
#    available_parameters = List
#    parameters = List(editor=EDITOR)

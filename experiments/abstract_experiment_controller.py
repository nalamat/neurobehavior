from copy import deepcopy, copy
from datetime import datetime, timedelta
from cns.data.persistence import add_or_update_object_node
from cns.data.h5_utils import get_or_append_node

from tdt import DSPProject
from tdt.device import RZ6
from cns import get_config

from enthought.pyface.api import error, confirm, YES, ConfirmationDialog
from enthought.pyface.timer.api import Timer
from enthought.etsconfig.api import ETSConfig
from enthought.traits.api import (Any, Instance, Enum, Dict, on_trait_change, 
        HasTraits, List, Button, Bool, Tuple, Callable, Int, Property,
        cached_property, Undefined, Event, TraitError, Str, Float)
from enthought.traits.ui.api import Controller, View, HGroup, Item, spring

from cns.widgets.toolbar import ToolBar
from enthought.savage.traits.ui.svg_button import SVGButton
from cns.widgets import icons

from PyQt4 import QtGui
from PyQt4.QtGui import QApplication

from enthought.traits.api import HasTraits, Dict, on_trait_change, Property, \
        cached_property

from .apply_revert_controller_mixin import ApplyRevertControllerMixin


import logging
log = logging.getLogger(__name__)

from cns import get_config
from .utils import get_save_file, load_instance, dump_instance


from physiology_experiment import PhysiologyExperiment
from physiology_paradigm import PhysiologyParadigm
from physiology_data import PhysiologyData
from physiology_controller import PhysiologyController

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

class AbstractExperimentController(ApplyRevertControllerMixin, Controller):
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
    
    physiology_handler = Instance(PhysiologyController)

    current_hw_att1 = Float(0)
    current_hw_att2 = Float(0)

    status = Property(Str, depends_on='state, current_setting')

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
        mesg = '{}\n\nDo you wish to stop the program?'.format(error)
        
        # Since this is a critical error, we should force the window to the
        # top so the user knows there is a problem. Typically this is
        # considered rude behavior in programming; however, experiments take
        # priority.
        self.info.ui.control.activateWindow()
        if confirm(self.info.ui.control, mesg, 'Error while running') == YES:
            self.stop(self.info)

    def notify(self, message):
        self.system_tray.showMessage('Neurobehavior notification', message)

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
                data_node = info.object.data_node
                node = get_or_append_node(data_node, 'physiology')
                data = PhysiologyData(store_node=node)
                experiment = PhysiologyExperiment(data=data, parent=info.object)
                handler = PhysiologyController(process=self.process,
                                               parent=self, state='client')
                experiment.edit_traits(handler=handler, parent=None)
                self.physiology_handler = handler

            # Create a system tray for notification messages.  Using popups do
            # not seem to work very well.  Either the popups are modal (in which
            # case they block the program from continuing to run) or they
            # dissappear below the main window.
            #self.system_tray = QtGui.QSystemTrayIcon(icon, info.ui.control)
            from os.path import dirname, join
            icon_path = join(dirname(__file__), 'psi_uppercase.svg')
            icon = QtGui.QIcon(icon_path)
            self.system_tray = QtGui.QSystemTrayIcon()
            self.system_tray.setIcon(icon)
            self.system_tray.setVisible(True)
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
        Handles starting an experiment

        Subclasses must implement `start_experiment`
        '''
        try:
            # setup_experiment should load the necessary circuits and
            # initialize the buffers. This data is required before the
            # hardware process is launched since the shared memory, locks and
            # pipelines must be created.
            self.setup_experiment(info)

            # Start the harware process
            self.process.start()

            if self.model.spool_physiology:
                self.physiology_handler.start()

            # Now that the process is started, we can configure the circuit
            # (e.g. read/write to tags) and gather the information we need to
            # run the experiment.
            self.initialize_context()
            self.start_experiment(info)

            # Save the start time in the model
            self.model.start_time = datetime.now()
            self.timer = Timer(100, self.run_tasks)
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
                    self.handle_error(e)
        self.tick_count += 1

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

    def set_attenuations(self, att1, att2, check=True):
        # TDT's built-in attenuators for the RZ6 function in 20 dB steps, so we
        # need to determine the next greater step size for the attenuator.  The
        # maximum hardware attenuation is 60 dB.
        log.debug('Attempting to change attenuation to %r and %r', att1, att2)

        if att1 is not None:
            hw1, sw1 = RZ6.split_attenuation(att1)
            if hw1 != self.current_hw_att1:
                if check and self.get_current_value('fixed_attenuation'):
                    raise ValueError, 'Cannot change primary attenuation'
                self.iface_behavior.set_tag('att1', hw1)
                self.current_hw_att1 = hw1
                #self.output_primary.hw_attenuation = hw1
                log.debug('Updated primary attenuation to %.2f', hw1)

        if att2 is not None:
            hw2, sw2 = RZ6.split_attenuation(att2)
            if hw2 != self.current_hw_att2:
                if check and self.get_current_value('fixed_attenuation'):
                    raise ValueError, 'Cannot change secondary attenuation'
                self.iface_behavior.set_tag('att2', hw2)
                self.current_hw_att2 = hw2
                #self.output_secondary.hw_attenuation = hw2
                log.debug('Updated secondary attenuation to %.2f', hw2)

    def set_expected_speaker_range(self, value):
        self._update_attenuators()

    def set_fixed_attenuation(self, value):
        self._update_attenuators()

    def set_speaker_equalize(self, value):
        self.output_primary.equalize = value
        self.output_secondary.equalize = value

    def _update_attenuators(self):
        if self.get_current_value('fixed_attenuation'):
            ranges = self.get_current_value('expected_speaker_range')
            ranges = [(s.frequency, s.max_level) for s in ranges]
            att1 = self.cal_primary.get_best_attenuation(ranges)
            att2 = self.cal_secondary.get_best_attenuation(ranges)
            log.debug('Best attenuations are %.2f and %.2f', att1, att2)
            self.set_attenuations(att1, att2, False)
            self.output_primary.fixed_attenuation = True
            self.output_secondary.fixed_attenuation = True
        else:
            self.output_primary.fixed_attenuation = False
            self.output_secondary.fixed_attenuation = False

    def log_trial(self, **kwargs):
        for key, value in self.context_log.items():
            if value:
                kwargs[key] = self.current_context[key]
        self.model.data.log_trial(**kwargs)

    def log_event(self, name, message, ts=None):
        if ts is None:
            ts = self.get_ts()
        self.model.data.log_event(ts, name, message)
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
        except AttributeError:
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

    def load_calibration(self, info):
        directory = get_config('CAL_ROOT')
        fd = FileDialog(action='open', default_directory=directory)
        if fd.open() == OK and fd.path <> '':
            pass


    calibration_window = Any

    def show_calibration(self, info):
        # TODO: add logic to bring calibration window back to front if the user
        # calls this function again rather than generating a second popup
        if self.calibration_window is None:
            from calibration_plot import CalibrationPlot
            calibrations = [self.cal_primary, self.cal_secondary]
            self.calibration_window = CalibrationPlot(calibrations=calibrations)
        self.calibration_window.edit_traits()

    def show_signal(self, info):
        pass

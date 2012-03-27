from enthought.pyface.api import error, information
from .cohort import Cohort, CohortViewHandler
import pickle
from cns.h5 import get_or_append_node
import sys
import tables
import os
from os.path import join
from importlib import import_module

from enthought.traits.api import Any, Trait, TraitError
from experiments import trial_setting
from cns import calibration

import logging
log = logging.getLogger(__name__)

from cns import get_config
from datetime import datetime

time_fmt = get_config('TIME_FORMAT')

class ExperimentLauncher(CohortViewHandler):

    args            = Any
    last_paradigm   = Trait(None, Any)

    def init(self, info):
        if not self.load_file(info):
            sys.exit()

    def launch_experiment(self, info, selected):
        '''
        Runs specified experiment type.  On successful completion of an
        experiment, marks the animal as processed and saves the last paradigm
        used.  If the experiment is launched but not run, changes to the
        paradigm will not be saved.
        '''

        filename = selected._store_filename
        pathname = selected._store_pathname
        with tables.openFile(filename, 'a', rootUEP=pathname) as fh:
            # We need to call prepare_experiment prior to loading a saved
            # paradigm.  prepare_experiment adds the roving parameters as traits
            # on the TrialSetting object.  If a paradigm is loaded before the
            # traits are added, wonky things may happen.
            store_node = get_or_append_node(fh.root, 'experiments')
            model, controller = prepare_experiment(self.args, store_node)
            model.animal = selected

            # Try to load settings from the last time the subject was run.  If
            # we cannot load the settings for whatever reason, notify the user
            # and fall back to the default settings.
            paradigm_node = get_or_append_node(store_node, 'last_paradigm')
            paradigm_name = get_experiment(self.args.type).node_name
            paradigm_hash = paradigm_name + '_' + '_'.join(self.args.rove)

            # Attempt to load the last used paradigm
            paradigm = None
            try:
                paradigm = paradigm_node._v_attrs[paradigm_hash]
            except KeyError as e:
                log.exception(e)
                mesg = 'No prior paradigm found'
                log.debug(mesg)
                information(info.ui.control, mesg)
            except pickle.UnpicklingError as e:
                log.exception(e)
                mesg = 'Prior settings found, but unable to load'
                log.debug(mesg)
                information(info.ui.control, mesg)

            try:
                if paradigm is not None:
                    log.debug('Using paradigm from last time this animal was run')
                    model.paradigm = paradigm
                elif self.last_paradigm is not None:
                    log.debug('Animal does not have any prior paradigm.')
                    model.paradigm = self.last_paradigm
                    mesg = 'Using paradigm from previous animal'
                    information(info.ui.control, mesg)
                    log.debug(mesg)
            except TraitError:
                log.debug('Prior paradigm is not compatible with experiment')
    
            try:
                model.edit_traits(parent=info.ui.control, kind='livemodal',
                                  handler=controller)
                # One very nice feature of PyTables is that it will
                # automatically pickle classes into strings that can be
                # stored as node attributes.
                paradigm_node._v_attrs[paradigm_hash] = model.paradigm
                self.last_paradigm = model.paradigm
                selected.processed = True
                log.debug('Saved paradigm for animal to the datafile')
            except AttributeError, e: 
                log.exception(e)
            except SystemError, e:
                from textwrap import dedent
                mesg = """\
                Could not launch experiment.  This likely means that you forgot to
                turn on a piece of equipment.  Please check and ensure that the RX6,
                RZ5 and PA5 are turned on.  If you still get this error message,
                please try power-cycling the rack.  If this still does not fix the
                error, power-cycle the computer as well.  
                
                Please remember that you need to give the equipment rack a minute to
                boot up once you turn it back on before attempting to launch an
                experiment.
                """
                error(info.ui.control, str(e) + '\n\n' + dedent(mesg))

    # Note the double underscore because the object trait is named _dclicked (it
    # already has a single underscore in it)
    def object__dclicked_changed(self, info):
        if info.initialized:
            self.launch_experiment(info, info.object._selected)

def prepare_experiment(args, store_node):

    '''
    Given the arguments passed in via the command-line, configure the
    Experiment, Controller, Data and Paradigm class accordingly and return an
    instance of the model and controller class.
    '''

    # The HDF5 file that is used for the data
    store_file = store_node._v_file

    # If the user did not specify a list of parameters that the data should be
    # grouped into before analysis (i.e. for computing the hit and false alarm
    # fractions), then use the parameters specified via rove as the analysis
    # parameters.
    if len(args.analyze) == 0:
        args.analyze = args.rove[:]

    # Load the experiment from the launchers folder.  args.type should be the
    # name of the corresponding file in the launchers folder (without the .py
    # extension)
    module = get_experiment(args.type)
    
    # Pull out the classes
    paradigm_class = module.Paradigm
    experiment_class = module.Experiment
    controller_class = module.Controller
    data_class = module.Data
    node_name = module.node_name

    # Create the experiment and data nodes. Hint! This is where you would
    # change the default pathname for the experiment if you wished.
    name = node_name + '_' + datetime.now().strftime(time_fmt)
    exp_node = store_file.createGroup(store_node, name)

    # Where the data is stored
    data_node = store_file.createGroup(exp_node, 'data')

    # Configure the TrialSetting/trial_setting_editor objects to contain the
    # parameters we wish to control in the experiment
    trial_setting.add_parameters(args.rove, paradigm_class, args.repeats)

    if args.att:
        # The user wants to specify values in terms of dB attenuation rather
        # than a calibrated dB SPL standard.  Prepare the calibration
        # accordingly.
        cal1 = calibration.Attenuation()
        cal2 = calibration.Attenuation()
    else:
        if args.cal is not None:
            cal1_filename, cal2_filename = args.cal
        else:
            cal1_filename = get_config('CAL_PRIMARY')
            cal2_filename = get_config('CAL_SECONDARY')

        cal1 = calibration.load_mat_cal(cal1_filename, args.equalized)
        log.debug('Loaded calibration file %s for primary', cal1_filename)
        cal2 = calibration.load_mat_cal(cal2_filename, args.equalized)
        log.debug('Loaded calibration file %s for secondary', cal2_filename)

    controller_args = {
            'cal_primary':      cal1,
            'cal_secondary':    cal2,
            'address':          args.address,
            }
    
    log.debug('store_node: %s', store_node)
    log.debug('data_node: %s', data_node)
    log.debug('exp_node: %s', exp_node)
    
    # Prepare the classes. This really is a lot of boilerplate to link up
    # parameters with paradigms, etc, to facilitate analysis
    paradigm = paradigm_class()
    data = data_class(store_node=data_node,
                      save_microphone=args.save_microphone)
    data.parameters = args.analyze
    model = experiment_class(
            store_node=store_node, 
            experiment_node=exp_node,
            data_node=data_node, 
            data=data,
            paradigm=paradigm,
            spool_physiology=args.physiology,
            )
    
    if args.analyze:
        model.plot_index = args.analyze[0]
        model.plot_group = args.analyze[1:]

    controller = controller_class(**controller_args)
    return model, controller

def test_experiment(args):
    '''
    Run experiment using a temporary file for the data
    '''
    # Create a temporary file to write the data to
    import tempfile
    tempname = 'neurobehavior_tmp.h5'
    filename = os.path.join(tempfile.gettempdir(), tempname)
    log.debug("Creating temporary file %s for testing", filename)
    launch_experiment(args, filename, True)
    # Once the program exists, remove the temporary file
    os.unlink(filename)
    log.debug("Deleted temporary file %s", filename)

def launch_experiment(args, filename, overwrite=False):
    if overwrite:
        mode = 'w'
        log.debug('Creating file %s for writing', filename)
    else:
        mode = 'a'
        log.debug('Opening file %s for appending', filename)
    handle = tables.openFile(filename, mode)
    model, controller = prepare_experiment(args, handle.root)
    model.configure_traits(handler=controller)
    handle.close()
    log.debug('Closing file %s', filename)

def profile_experiment(args):
    import cProfile
    profile_data_file = join(get_config('TEMP_ROOT'), 'profile.dmp')
    cProfile.runctx('test_experiment(args)', globals(), {'args': args},
                    filename=profile_data_file)

    # Once experiment is done, print out some statistics
    import pstats
    p = pstats.Stats(profile_data_file)
    p.strip_dirs().sort_stats('cumulative').print_stats(50)

#def objgraph_experiment(args):
#    profile_data_file = join(get_config('TEMP_ROOT'), 'profile.dmp')
#    cProfile.runctx('test_experiment(args)', globals(), {'args': args},
#                    filename=profile_data_file)
#
#    # Once experiment is done, print out some statistics
#    import pstats
#    p = pstats.Stats(profile_data_file)
#    p.strip_dirs().sort_stats('cumulative').print_stats(50)


def launch_experiment_selector(args):
    handler = ExperimentLauncher(args=args)
    Cohort().configure_traits(handler=handler, view='detailed_view')

def inspect_experiment(args):
    '''
    Print out parameters available for requested paradigm
    '''
    # Get a list of the parameters available in the paradigm
    cls = get_experiment(args.type).Paradigm
    cls.pp_parameters()

def get_invalid_parameters(args):
    '''
    Check the list of parameters provided by the user and return the invalid
    parameters
    '''
    parameters = set(args.rove)
    parameters.update(args.analyze)
    cls = get_experiment(args.type).Paradigm
    return cls.get_invalid_parameters(parameters)

def get_experiment(etype):
    return import_module('paradigms.{}'.format(etype))

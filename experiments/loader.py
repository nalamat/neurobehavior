from enthought.pyface.api import error, information
from cns.data.ui.cohort import CohortView, CohortViewHandler
from cns.data import persistence
from cns.data.h5_utils import get_or_append_node
import sys
import tables
import imp
import os
from os.path import join, dirname, basename, exists

from enthought.traits.api import Any, Trait, TraitError, Bool, Str
from enthought.traits.ui.api import View, Item, VGroup, HGroup, Spring
from experiments import trial_setting
from enthought.traits.api import Float
from neurogen import calibration

import logging
log = logging.getLogger(__name__)

# Import the experiments
from cns.data.ui.cohort import CohortEditor, CohortView, CohortViewHandler
from cns.data.h5_utils import append_node, append_date_node
from cns import get_config

class ExperimentCohortView(CohortView):

    path = get_config('COHORT_ROOT')
    wildcard = get_config('COHORT_WILDCARD')

    traits_view = View(
        VGroup(
            HGroup(
                Item('object.cohort.description', style='readonly',
                    springy=True),
                show_border=True,
                ),
            Item('object.cohort.animals', editor=CohortEditor(),
                 show_label=False, style='readonly'),
        ),
        title='Cohort',
        height=400,
        width=600,
        resizable=True,
    )

class ExperimentLauncher(CohortViewHandler):

    args            = Any
    last_paradigm   = Trait(None, Any)

    def init(self, info):
        if not self.load_file(info):
            sys.exit()

    def load_paradigm(self, info, paradigm_node, paradigm_hash):
        try:
            return persistence.load_object(paradigm_node, paradigm_hash)
        except tables.NoSuchNodeError:
            mesg = 'No prior paradigm found.  Creating new paradigm.'
            log.debug(mesg)
            information(info.ui.control, mesg)
        except (TraitError, ImportError, persistence.PersistenceReadError), e:
            mesg = 'Unable to load prior settings.  Creating new paradigm.'
            log.debug(mesg)
            log.exception(e)
            error(info.ui.control, mesg)

    def launch_experiment(self, info, selected):
        '''
        Runs specified experiment type.  On successful completion of an
        experiment, marks the animal as processed and saves the last paradigm
        used.  If the experiment is launched but not run, changes to the
        paradigm will not be saved.
        '''

        try:
            item = selected
            if item.store_node._v_isopen:
                animal_node = item.store_node
            else:
                log.debug('Opening node %r for %r', item.store_node, item)
                file = tables.openFile(item.store_node_source, 'a',
                                       rootUEP=item.store_node_path)
                animal_node = file.root

            # We need to call prepare_experiment prior to loading a saved
            # paradigm.  prepare_experiment adds the roving parameters as traits
            # on the TrialSetting object.  If a paradigm is loaded before the
            # traits are added, wonky things may happen.
            store_node = get_or_append_node(animal_node, 'experiments')
            model, controller = prepare_experiment(self.args, store_node)
            model.animal = item

            # Try to load settings from the last time the subject was run.  If
            # we cannot load the settings for whatever reason, notify the user
            # and fall back to the default settings.
            paradigm_node = get_or_append_node(store_node, 'last_paradigm')
            paradigm_name = get_experiment(self.args.type).node_name
            paradigm_hash = paradigm_name + '_' + '_'.join(self.args.rove)

            paradigm = self.load_paradigm(info, paradigm_node, paradigm_hash)

            try:
                if paradigm is not None:
                    log.debug('Using paradigm from last time this animal was run')
                    model.paradigm = paradigm
                elif self.last_paradigm is not None:
                    log.debug('Animal does not have any prior paradigm.')
                    log.debug('Using paradigm from previous animal.')
                    model.paradigm = self.last_paradigm
            except TraitError:
                log.debug('Prior paradigm is not compatible with experiment')
    
            ui = model.edit_traits(parent=info.ui.control, kind='livemodal',
                    handler=controller)

            if ui.result:
                persistence.add_or_update_object(model.paradigm, paradigm_node,
                        paradigm_hash)
                item.processed = True
                self.last_paradigm = model.paradigm
            
            # Close the file if we opened it
            try: 
                file.close()
            except NameError: 
                pass
            
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

    def object_dclicked_changed(self, info):
        if info.initialized:
            self.launch_experiment(info, info.object.selected)

def prepare_experiment(args, store_node):
    if len(args.analyze) == 0:
        args.analyze = args.rove[:]
    module = get_experiment(args.type)
    
    # Find the classes
    paradigm_class = module.Paradigm
    experiment_class = module.Experiment
    controller_class = module.Controller
    data_class = module.Data
    node_name = module.node_name

    exp_node = append_date_node(store_node, node_name + '_')
    data_node = append_node(exp_node, 'data')

    # Configure the TrialSetting/trial_setting_editor objects to contain the
    # parameters we wish to control in the experiment
    trial_setting.add_parameters(args.rove, paradigm_class, args.repeats)

    # The user wants to specify values in terms of dB attenuation rather than a
    # calibrated dB SPL standard.  Prepare the calibration accordingly.
    if args.att:
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
    data = data_class(store_node=data_node)
    data.parameters = args.analyze
    model = experiment_class(
            store_node=store_node, 
            exp_node=exp_node,
            data_node=data_node, 
            data=data,
            paradigm=paradigm,
            spool_physiology=args.physiology,
            )
    if len(args.analyze) > 0:
        model.plot_index = args.analyze[0]
        model.plot_group=args.analyze[1:]
    elif len(args.rove) > 0:
        model.plot_index = args.rove[0]
        model.plot_group=args.rove[1:]
    print controller_args
    controller = controller_class(**controller_args)
    return model, controller

def test_experiment(args):
    '''
    Run experiment using a temporary file for the data
    '''
    # Create a temporary file to write the data to
    import tempfile
    tempname = 'neurobehavior_tmp.h5'
    tempdir = tempfile.gettempdir()
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

def launch_experiment_selector(args):
    handler = ExperimentLauncher(args=args)
    ExperimentCohortView().configure_traits(handler=handler)

def inspect_experiment(args):
    '''
    Print out parameters available for requested paradigm
    '''
    
    # Get a list of the parameters available in the paradigm
    p = get_experiment(args.type).Paradigm
    parameters = sorted(list(p.get_parameter_info().items()))

    # Add the column headings
    parameters.insert(0, ('Variable Name', 'Label'))
    parameters.insert(1, ('-------------', '-----'))

    # Determine the padding we need for the columns
    col_paddings = []
    for i in range(len(parameters[0])):
        sizes = [len(row[i]) if row[i] != None else 0 for row in parameters]
        col_paddings.append(max(sizes))

    # Pretty print the list
    print '\n'
    for i, row in enumerate(parameters):
        print row[0].rjust(col_paddings[0]+2) + ' ',
        if row[1] is not None:
            print row[1].ljust(col_paddings[1]+2)
        else:
            print ''

def get_invalid_parameters(args):
    parameters = set(args.rove)
    parameters.update(args.analyze)
    paradigm = get_experiment(args.type).Paradigm
    return [p for p in parameters if p not in paradigm.get_parameters()]

def get_experiment(etype):
    from importlib import import_module
    return import_module('launchers.{}'.format(etype))

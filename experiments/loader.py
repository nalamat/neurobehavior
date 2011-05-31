import cPickle as pickle

from enthought.pyface.api import error, information
from cns.data.ui.cohort import CohortView, CohortViewHandler
from cns.data import persistence
from cns.data.h5_utils import get_or_append_node
import sys
import tables
from os.path import join

from enthought.traits.api import Any, Trait, TraitError, Bool, Str
from enthought.traits.ui.api import View, Item, VGroup, HGroup, Spring
from experiments.trial_setting import TrialSetting, trial_setting_editor
from enthought.traits.api import Float
from enthought.traits.ui.api import ObjectColumn

import logging
log = logging.getLogger(__name__)

# Import the experiments
from cns.data.ui.cohort import CohortEditor, CohortView, CohortViewHandler
from cns.data.h5_utils import append_node, append_date_node

from scripts import settings

#import imp
#import os
#settings_file = os.path.dirname(os.ENVIRON['NEUROBEHAVIOR_SETTINGS']) 
#imp.find_module('settings', os.ENVIRON['NEUROBEHAVIOR_SETTINGS'])

class ExperimentCohortView(CohortView):

    #path = settings.COHORT_ROOT
    #wildcard = settings.COHORT_WILDCARD

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
            paradigm_name = get_experiment(self.args.type)['node_name']
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
    # Load the experiment classes
    e = get_experiment(args.type)
    node_name = e['node_name'] + '_' + '_'.join(args.rove)
    exp_node = append_date_node(store_node, node_name + '_')
    data_node = append_node(exp_node, 'data')

    experiment_class, experiment_args = e['experiment']
    data_class, data_args = e['data']
    paradigm_class, paradigm_args = e['paradigm']
    controller_class, controller_args = e['controller']

    # Configure the TrialSetting/trial_setting_editor objects to contain the
    # parameters we wish to control in the experiment
    columns = []
    for parameter in args.rove:
        label = paradigm_class.class_traits()[parameter].label
        try:
            trait = Float(label=label, store='attribute')
            TrialSetting.add_class_trait(parameter, trait)
        except TraitError:
            pass
        finally:
            column = ObjectColumn(name=parameter, label=label, width=75)
            columns.append(column)
    TrialSetting.parameters = args.rove
    trial_setting_editor.columns = columns

    # Load the calibration data
    #controller_args['cal_primary'] = neurogen.load_mat_cal(settings.CAL_PRIMARY)
    #controller_args['cal_secondary'] = neurogen.load_mat_cal(settings.CAL_SECONDARY)

    # Prepare the classes.  This really is a lot of boilerplate to link up
    # parameters with paradigms, etc, to facilitate analysis
    paradigm = paradigm_class(**paradigm_args)
    data = data_class(store_node=data_node, **data_args)
    data.parameters = args.analyze
    model = experiment_class(
            store_node=store_node, 
            exp_node=exp_node,
            data_node=data_node, 
            data=data,
            paradigm=paradigm,
            spool_physiology=args.physiology,
            **experiment_args
            )
    if len(args.analyze) > 0:
        model.plot_index = args.analyze[0]
        model.plot_group=args.analyze[1:]
    elif len(args.rove) > 0:
        model.plot_index = args.rove[0]
        model.plot_group=args.rove[1:]
    controller = controller_class(**controller_args)
    return model, controller

def test_experiment(args):
    #from cns import TEMP_ROOT
    filename = join(settings.TEMP_ROOT, 'test_experiment.hd5')
    file = tables.openFile(filename, 'w')
    model, controller = prepare_experiment(args, file.root)
    model.configure_traits(handler=controller)

def profile_experiment(args):
    #from cns import TEMP_ROOT
    import cProfile
    profile_data_file = join(settings.TEMP_ROOT, 'profile.dmp')
    cProfile.runctx('test_experiment(args)', globals(), {'args': args},
            filename=profile_data_file)

    # Once experiment is done, print out some statistics
    import pstats
    p = pstats.Stats(profile_data_file)
    p.strip_dirs().sort_stats('cumulative').print_stats(50)

def launch_experiment(args):
    handler = ExperimentLauncher(args=args)
    ExperimentCohortView().configure_traits(handler=handler)

def inspect_experiment(args):
    '''
    Print out parameters available for requested paradigm
    '''
    e = get_experiment(args.type)
    p = e['paradigm'][0]()
    parameters = list(p.parameter_info.items())
    parameters.sort()
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
    paradigm = get_experiment(args.type)['paradigm'][0]()
    return [p for p in parameters if p not in paradigm.get_parameters()]

import re

# Define the classes required for each experiment.
EXPERIMENTS = {
        'basic_characterization': {
            'experiment':   ('AbstractExperiment', {}), 
            'paradigm':     ('BasicCharacterizationParadigm', {}),
            'controller':   ('BasicCharacterizationController', {}), 
            'data':         ('AbstractExperimentData', {}),
            'node_name':    'BasicCharacterizationExperiment',
            },
        'positive_training': {
            'experiment':   ('PositiveStage1Experiment', {}),
            'paradigm':     ('PositiveStage1Paradigm', {}),
            'controller':   ('PositiveStage1Controller', {}),
            'data':         ('PositiveStage1Data', {}),
            'node_name':    'PositiveStage1Experiment',
            },
        'positive_am_noise': {
            'experiment':   ('AbstractPositiveExperiment', {}), 
            'paradigm':     ('PositiveAMNoiseParadigm', {}), 
            'controller':   ('PositiveAMNoiseController', {}), 
            'data':         ('PositiveData',  {}),
            'node_name':    'PositiveAMNoiseExperiment',
            },
        'positive_dt': {
            'experiment':   ('AbstractPositiveExperiment', {}), 
            'paradigm':     ('PositiveDTParadigm', {}),
            'controller':   ('PositiveDTController', {}), 
            'data':         ('PositiveData', {}),
            'node_name':    'PositiveDTExperiment',
            },
        'aversive_fm': {
            'experiment':   ('AbstractAversiveExperiment', {}), 
            'paradigm':     ('AversiveFMParadigm', {}),
            'controller':   ('AversiveFMController', {}), 
            'data':         ('AversiveData', {}),
            'node_name':    'AversiveFMExperiment',
            },
        'aversive_dt': {
            'experiment':   ('AbstractAversiveExperiment', {}), 
            'paradigm':     ('AversiveDTParadigm', {}),
            'controller':   ('AversiveDTController', {}), 
            'data':         ('AversiveData', {}),
            'node_name':    'AversiveDTExperiment',
            },
        'aversive_am_noise': {
            'experiment':   ('AbstractAversiveExperiment', {}), 
            'paradigm':     ('AversiveAMNoiseParadigm', {}),
            'controller':   ('AversiveAMNoiseController', {}), 
            'data':         ('AversiveData', {}),
            'node_name':    'AversiveAMNoiseExperiment',
            },
        'aversive_noise_masking': {
            'experiment':   ('AbstractAversiveExperiment', {}), 
            'paradigm':     ('AversiveNoiseMaskingParadigm', {}),
            'controller':   ('AversiveNoiseMaskingController', {}), 
            'data':         ('AversiveData', {}),
            'node_name':    'AversiveNoiseMaskingExperiment',
            },
        }

def convert(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

def get_experiment(etype):
    from importlib import import_module
    experiment = EXPERIMENTS[etype].copy()
    for k, v in experiment.items():
        if k != 'node_name' and type(v[0]) == type(''):
            try:
                klass = __import__(v[0])
            except:
                module = '.' + convert(v[0])
                module = import_module(module, package='experiments')
                klass = getattr(module, v[0])
            experiment[k] = (klass, v[1])
    return experiment

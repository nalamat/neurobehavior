from enthought.etsconfig.api import ETSConfig
ETSConfig.toolkit='qt4'

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

# Aversive
from abstract_aversive_experiment import AbstractAversiveExperiment
from aversive_data_v3 import RawAversiveData as AversiveData
# Aversive FM
from aversive_fm_paradigm import AversiveFMParadigm
from aversive_fm_controller import AversiveFMController
# Aversive AM Noise
from aversive_am_noise_paradigm import AversiveAMNoiseParadigm
from aversive_am_noise_controller import AversiveAMNoiseController
# Aversive Noise Masking
from aversive_noise_masking_paradigm import AversiveNoiseMaskingParadigm
from aversive_noise_masking_controller import AversiveNoiseMaskingController
# Positive
from abstract_positive_experiment import AbstractPositiveExperiment
from positive_data import PositiveData
# Positive AM Noise
from positive_am_noise_paradigm import PositiveAMNoiseParadigm
from positive_am_noise_controller import PositiveAMNoiseController
from positive_am_noise_data import PositiveAMNoiseData
# Positive DT
from positive_dt_experiment import PositiveDTExperiment
from positive_dt_paradigm import PositiveDTParadigm
from positive_dt_controller import PositiveDTController
from positive_dt_data import PositiveDTData
# Basic Characterization
from abstract_experiment import AbstractExperiment
from basic_characterization_paradigm import BasicCharacterizationParadigm
from basic_characterization_controller import BasicCharacterizationController
#from physiology_data_mixin import PhysiologyDataMixin
from abstract_experiment_data import AbstractExperimentData

from cns.data.h5_utils import append_node, append_date_node

class ExperimentCohortView(CohortView):

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
            
            # Try to load settings from the last time the subject was run.  If
            # we cannot load the settings for whatever reason, notify the user
            # and fall back to the default settings.
            store_node = get_or_append_node(animal_node, 'experiments')
            paradigm_node = get_or_append_node(store_node, 'last_paradigm')
            #paradigm_name = self.experiment.__name__
            paradigm_name = EXPERIMENTS[self.args.type]['node_name']
            paradigm = None
            try:
                paradigm = persistence.load_object(paradigm_node, paradigm_name)
            except tables.NoSuchNodeError:
                mesg = 'No prior paradigm found.  Creating new paradigm.'
                log.debug(mesg)
                information(info.ui.control, mesg)
            except TraitError, e:
                mesg = 'Unable to load prior settings.  Creating new paradigm.'
                log.debug(mesg)
                log.exception(e)
                error(info.ui.control, mesg)
            except ImportError, e:
                mesg = 'Unable to load prior settings.  Creating new paradigm.'
                log.debug(mesg)
                log.exception(e)
                error(info.ui.control, mesg)
            except persistence.PersistenceReadError, e:
                mesg = 'Unable to load prior settings.  Creating new paradigm.'
                log.debug(mesg)
                log.exception(e)
                error(info.ui.control, mesg)

            model, controller = prepare_experiment(self.args)

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
                        paradigm_name)
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
    e = EXPERIMENTS[args.type]
    exp_node = append_date_node(store_node, e['node_name'] + '_')
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
        TrialSetting.add_class_trait(parameter, Float)
        column = ObjectColumn(name=parameter, label=label, width=75)
        columns.append(column)
    TrialSetting.parameters = args.rove
    trial_setting_editor.columns = columns

    # Prepare the classes.  This really is a lot of boilerplate to link up
    # parameters with paradigms, etc, to facilitate analysis

    paradigm = paradigm_class(**paradigm_args)
    data = data_class(store_node=data_node, **data_args)
    model = experiment_class(
            store_node=store_node, 
            exp_node=exp_node,
            data_node=data_node, 
            data=data,
            plot_index=args.analyze[0],
            plot_group=args.analyze[1:],
            paradigm=paradigm,
            spool_physiology=args.physiology,
            **experiment_args
            )
    controller = controller_class(**controller_args)
    return model, controller

def test_experiment(args):
    from cns import TEMP_ROOT
    filename = join(TEMP_ROOT, 'test_experiment.hd5')
    file = tables.openFile(filename, 'w')
    model, controller = prepare_experiment(args, file.root)
    model.configure_traits(handler=controller)

def profile_experiment(args):
    from cns import TEMP_ROOT
    import cProfile
    profile_data_file = join(TEMP_ROOT, 'profile.dmp')
    cProfile.run('test_experiment("%s", %s)' % (args.type,
        args.physiology), profile_data_file)

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
    e = EXPERIMENTS[args.type]
    p = e['paradigm'][0]()
    parameters = [(n, p.trait(n).label) for n in p.editable_traits()]

    # Determine the padding we need for the columns
    col_paddings = []
    for i in range(len(parameters[0])):
        sizes = [len(row[i]) if row[i] != None else 0 for row in parameters]
        col_paddings.append(max(sizes))

    # Pretty print the list
    for row in parameters:
        print row[0].rjust(col_paddings[0]+2),
        if row[1] is not None:
            print row[1].ljust(col_paddings[1]+2)
        else:
            print ''

def get_invalid_parameters(args):
    parameters = set(args.rove)
    parameters.update(args.analyze)
    paradigm = EXPERIMENTS[args.type]['paradigm'][0]()
    valid_parameters = paradigm.editable_traits()
    return [p for p in parameters if p not in valid_parameters]

# Define the classes required for each experiment.
EXPERIMENTS = {
        'basic_characterization': {
            'experiment':   (AbstractExperiment, {}), 
            'paradigm':     (BasicCharacterizationParadigm, {}),
            'controller':   (BasicCharacterizationController, {}), 
            'data':         (AbstractExperimentData, {}),
            'node_name':    'BasicCharacterizationExperiment',
            },
        'positive_am_noise': {
            'experiment':   (AbstractPositiveExperiment, {}), 
            'paradigm':     (PositiveAMNoiseParadigm, {}), 
            'controller':   (PositiveAMNoiseController, {}), 
            'data':         (PositiveData,  {}),
            'node_name':    'PositiveAMNoiseExperiment',
            },
        'positive_dt': {
            'experiment':   (PositiveDTExperiment, {}), 
            'paradigm':     (PositiveDTParadigm, {}),
            'controller':   (PositiveDTController, {}), 
            'data':         (PositiveData, {}),
            'node_name':    'PositiveDTExperiment',
            },
        'aversive_fm': {
            'experiment':   (AbstractAversiveExperiment, {}), 
            'paradigm':     (AversiveFMParadigm, {}),
            'controller':   (AversiveFMController, {}), 
            'data':         (AversiveData, {}),
            'node_name':    'AversiveFMExperiment',
            },
        'aversive_am_noise': {
            'experiment':   (AbstractAversiveExperiment, {}), 
            'paradigm':     (AversiveAMNoiseParadigm, {}),
            'controller':   (AversiveAMNoiseController, {}), 
            'data':         (AversiveData, {}),
            'node_name':    'AversiveAMNoiseExperiment',
            },
        'aversive_noise_masking': {
            'experiment':   (AbstractAversiveExperiment, {}), 
            'paradigm':     (AversiveNoiseMaskingParadigm, {}),
            'controller':   (AversiveNoiseMaskingController, {}), 
            'data':         (AversiveData, {}),
            'node_name':    'AversiveNoiseMaskingExperiment',
            },
        }

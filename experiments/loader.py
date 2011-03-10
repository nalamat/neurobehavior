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

import logging
log = logging.getLogger(__name__)

# Import the experiments
from cns.data.ui.cohort import CohortEditor, CohortView, CohortViewHandler

# Aversive
from abstract_aversive_experiment import AbstractAversiveExperiment
from aversive_data import RawAversiveData as AversiveData
# Aversive FM
from aversive_fm_paradigm import AversiveFMParadigm
from aversive_fm_controller import AversiveFMController
# Aversive AM Noise
from aversive_am_noise_paradigm import AversiveAMNoiseParadigm
from aversive_am_noise_controller import AversiveAMNoiseController

# Positive
from abstract_positive_experiment import AbstractPositiveExperiment
from positive_data import PositiveData
# Positive AM Noise
from positive_am_noise_paradigm import PositiveAMNoiseParadigm
from positive_am_noise_controller import PositiveAMNoiseController
# Positive DT
from positive_dt_experiment import PositiveDTExperiment
from positive_dt_paradigm import PositiveDTParadigm
from positive_dt_controller import PositiveDTController
from positive_dt_data import PositiveDTData

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

    experiment_class    = Any
    paradigm_class      = Any
    controller_class    = Any
    data_class          = Any
    node_name           = Str
    spool_physiology    = Bool(True)

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
            paradigm_name = self.experiment.__name__
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
                
            exp_node = append_date_node(store_node, self.node_name + '_')
            data_node = append_node(exp_node, 'data')

            model = self.experiment_class(
                    store_node=store_node, 
                    exp_node=exp_node,
                    data_node=data_node, 
                    animal=item,
                    data=self.data_class(store_node=data_node),
                    paradigm=self.paradigm_class(),
                    spool_physiology=self.spool_physiology,
                    )
            
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
                    handler=self.controller_class())

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

def test_experiment(etype, spool_physiology):
    from cns import TEMP_ROOT
    filename = join(TEMP_ROOT, 'test_experiment.hd5')
    file = tables.openFile(filename, 'w')
    store_node = file.root

    e = EXPERIMENTS[etype]
    pre = e['node_name'] + '_'
    exp_node = append_date_node(store_node, pre)
    data_node = append_node(exp_node, 'data')

    model = e['experiment_class'](
            store_node=store_node, 
            exp_node=exp_node,
            data_node=data_node, 
            data=e['data_class'](store_node=data_node),
            paradigm=e['paradigm_class'](),
            spool_physiology=spool_physiology,
            )
    model.configure_traits(handler=e['controller_class']())

def profile_experiment(etype, spool_physiology=False):
    from cns import TEMP_ROOT
    import cProfile
    profile_data_file = join(TEMP_ROOT, 'profile.dmp')
    cProfile.run('test_experiment("%s", %s)' % (etype, spool_physiology),
            profile_data_file)

    # Once experiment is done, print out some statistics
    import pstats
    p = pstats.Stats(profile_data_file)
    p.strip_dirs().sort_stats('cumulative').print_stats(50)

def launch_experiment(etype, spool_physiology=False, profile=False):
    handler = ExperimentLauncher(spool_physiology=spool_physiology,
            **EXPERIMENTS[etype])
    ExperimentCohortView().configure_traits(handler=handler)

EXPERIMENTS = {
        'positive_am_noise': {
            'experiment_class': AbstractPositiveExperiment, 
            'paradigm_class': PositiveAMNoiseParadigm,
            'controller_class': PositiveAMNoiseController, 
            'data_class': PositiveData,
            'node_name': 'PositiveAMNoiseExperiment',
            },
        'positive_dt': {
            'experiment_class': PositiveDTExperiment, 
            'paradigm_class': PositiveDTParadigm,
            'controller_class': PositiveDTController, 
            'data_class': PositiveDTData,
            'node_name': 'PositiveDTExperiment',
            },
        'aversive_fm': {
            'experiment_class': AbstractAversiveExperiment, 
            'paradigm_class': AversiveFMParadigm,
            'controller_class': AversiveFMController, 
            'data_class': AversiveData,
            'node_name': 'AversiveFMExperiment',
            },
        'aversive_am_noise': {
            'experiment_class': AbstractAversiveExperiment, 
            'paradigm_class': AversiveAMNoiseParadigm,
            'controller_class': AversiveAMNoiseController, 
            'data_class': AversiveData,
            'node_name': 'AversiveAMNoiseExperiment',
            },
        }

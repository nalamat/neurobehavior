from enthought.etsconfig.api import ETSConfig
ETSConfig.toolkit='qt4'

from enthought.pyface.api import error
from cns.data.ui.cohort import CohortView, CohortViewHandler
from cns.data import persistence
from cns.data.h5_utils import get_or_append_node
import sys
import tables
from os.path import join
from enthought.traits.api import Any, Trait, TraitError
from enthought.traits.ui.api import View, Item

import logging
log = logging.getLogger(__name__)

# Import the experiments
from positive_stage1_experiment import PositiveStage1Experiment
from positive_experiment import PositiveExperiment
from aversive_fm_experiment import AversiveFMExperiment
from aversive_am_noise_experiment import AversiveAMNoiseExperiment
from aversive_noise_masking_experiment import AversiveNoiseMaskingExperiment

class ExperimentLauncher(CohortViewHandler):

    last_paradigm = Trait(None, Any)

    def init(self, info):
        if not self.load_file(info):
            sys.exit()

    def launch_experiment(self, info, selected, etype):
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
            
            store_node = get_or_append_node(animal_node, 'experiments')
            paradigm_node = get_or_append_node(store_node, 'last_paradigm')
            paradigm_name = etype.__name__
            try:
                paradigm = persistence.load_object(paradigm_node, paradigm_name)
            except tables.NoSuchNodeError:
                log.debug('No prior paradigm found.  Creating new paradigm.')
                paradigm = None
            except TraitError, e:
                log.debug('Prior paradigm found, but was unable to load.')
                log.exception(e)
                paradigm = None
            except ImportError, e:
                log.debug('Old paradigm found, but could not be loaded')
                log.exception(e)
                paradigm = None
                
            model = etype(store_node=store_node, animal=item)
            
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
    
            ui = model.edit_traits(parent=info.ui.control, kind='livemodal')
            if ui.result:
                #persistence.delete_object(paradigm_node, paradigm_name)
                persistence.add_or_update_object(model.paradigm, paradigm_node,
                        paradigm_name)
                item.processed = True
                self.last_paradigm = model.paradigm
            
            # Close the file if we opened it
            try: file.close()
            except NameError: pass
            
        except AttributeError, e: 
            log.error(e)
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

    # Functions to launch the different experiments from the context menu.  The options
    # for the context menu are defined in cns.data.ui.cohort (in the animal_editor).  That
    # really should be moved to this file since where it currently is located is not
    # obvious.

    # When the context menu item is selected, it calls the function specified by "action" with
    # two arguments, info (a handle to the current window) and the selected item.
    
    def launch_appetitive(self, info, selected):
        self.launch_experiment(info, selected[0], PositiveExperiment)

    def launch_aversive_am_noise(self, info, selected):
        self.launch_experiment(info, selected[0], AversiveAMNoiseExperiment)

    def launch_aversive_fm(self, info, selected):
        self.launch_experiment(info, selected[0], AversiveFMExperiment)

    def launch_appetitive_stage1(self, info, selected):
        self.launch_experiment(info, selected[0], PositiveStage1Experiment)

    def launch_aversive_noise_masking(self, info, selected):
        self.launch_experiment(info, selected[0], AversiveNoiseMaskingExperiment)

def load_experiment_launcher():
    CohortView().configure_traits(view='detailed_view', handler=ExperimentLauncher())

def test_experiment(etype):
    import tables
    test_file = tables.openFile('test.hd5', 'w')
    if not etype.endswith('Experiment'):
        etype += 'Experiment'
    experiment_class = globals()[etype]
    experiment = experiment_class(store_node=test_file.root)
    experiment.configure_traits()

def profile_experiment(etype):
    import cProfile
    cProfile.run('test_experiment("%s")' % etype, 'profile.dmp')
    import pstats
    p = pstats.Stats('profile.dmp')
    p.strip_dirs().sort_stats('cumulative').print_stats(50)

if __name__ == '__main__':
    profile_experiment(sys.argv[1])

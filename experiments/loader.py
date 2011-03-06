from enthought.etsconfig.api import ETSConfig
ETSConfig.toolkit='qt4'

from enthought.pyface.api import error, information
from cns.data.ui.cohort import CohortView, CohortViewHandler
from cns.data import persistence
from cns.data.h5_utils import get_or_append_node
import sys
import tables
from os.path import join

from enthought.traits.api import Any, Trait, TraitError, Bool
from enthought.traits.ui.api import View, Item, VGroup, HGroup

import logging
log = logging.getLogger(__name__)

# Import the experiments
from positive_stage1_experiment import PositiveStage1Experiment
from positive_am_noise_experiment import PositiveAMNoiseExperiment
from positive_dt_experiment import PositiveDTExperiment
from aversive_fm_experiment import AversiveFMExperiment
from aversive_am_noise_experiment import AversiveAMNoiseExperiment
from aversive_noise_masking_experiment import AversiveNoiseMaskingExperiment

from cns.data.ui.cohort import CohortEditor, CohortView, CohortViewHandler

from enthought.traits.ui.menu import Menu, Action

cohort_editor = CohortEditor(menu=Menu(
    # This is a list of the different "actions" one can call for each of the
    # animals in the cohort file.  The action is a function defined on the
    # handler.  All of these actions are currently tied to functions that launch
    # the appropriate experiment.  Name is the string that should be displayed
    # in the context menu (i.e.  the right-click pop-up menu).  action is the
    # function on the controller/handler that should be called when that
    # particular menu item is selected.  
    Action(name='Appetitive (temporal integration)',
           action='launch_appetitive_dt'),
    Action(name='Appetitive (AM noise)',
           action='launch_appetitive_am_noise'),
    Action(name='Appetitive (Stage 1)', action='launch_appetitive_stage1'),
    Action(name='Aversive (FM)', action='launch_aversive_fm'),
    Action(name='Aversive (AM Noise)', action='launch_aversive_am_noise'),
    Action(name='Aversive (Noise Masking)',
           action='launch_aversive_noise_masking'),
    ))

class ExperimentCohortView(CohortView):

    acquire_physiology = Bool(False)

    traits_view = View(
        VGroup(
            HGroup(
                Item('object.cohort.description', style='readonly'),
                Item('acquire_physiology'),
                ),
            Item('object.cohort.animals', editor=cohort_editor,
                 show_label=False, style='readonly'),
        ),
        title='Cohort',
        height=400,
        width=600,
        resizable=True,
    )

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
            
            # Try to load settings from the last time the subject was run.  If
            # we cannot load the settings for whatever reason, notify the user
            # and fall back to the default settings.
            store_node = get_or_append_node(animal_node, 'experiments')
            paradigm_node = get_or_append_node(store_node, 'last_paradigm')
            paradigm_name = etype.__name__
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
    
            ph = model.edit_traits(parent=info.ui.control, kind='live',
                view='physiology_view')
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

    # Functions to launch the different experiments from the context menu.  The
    # options for the context menu are defined in cns.data.ui.cohort (in the
    # animal_editor).  That really should be moved to this file since where it
    # currently is located is not obvious.

    # When the context menu item is selected, it calls the function specified by
    # "action" with two arguments, info (a handle to the current window) and the
    # selected item.

    def launch_appetitive_am_noise(self, info, selected):
        self.launch_experiment(info, selected[0], PositiveAMNoiseExperiment)
    
    def launch_appetitive_dt(self, info, selected):
        self.launch_experiment(info, selected[0], PositiveDTExperiment)

    def launch_aversive_am_noise(self, info, selected):
        self.launch_experiment(info, selected[0], AversiveAMNoiseExperiment)

    def launch_aversive_fm(self, info, selected):
        self.launch_experiment(info, selected[0], AversiveFMExperiment)

    def launch_appetitive_stage1(self, info, selected):
        self.launch_experiment(info, selected[0], PositiveStage1Experiment)

    def launch_aversive_noise_masking(self, info, selected):
        self.launch_experiment(info, selected[0], AversiveNoiseMaskingExperiment)

def load_experiment_launcher():
    ExperimentCohortView().configure_traits(handler=ExperimentLauncher())

def test_experiment(etype):
    # Since we are testing our experiment paradigm, we need to provide a
    # temporary HDF5 file (i.e. a "dummy" cohort file) that the experiment can
    # save its data to.
    import tables
    from cns import TEMP_ROOT
    file_name = join(TEMP_ROOT, 'test.h5')
    test_file = tables.openFile(file_name, 'w')

    if not etype.endswith('Experiment'):
        etype += 'Experiment'
    log.debug("Looking for experiment %s", etype)
    experiment_class = globals()[etype]
    log.debug("Setting up experiment %s", etype)
    experiment = experiment_class(store_node=test_file.root)
    log.debug("Initializing GUI for %s", etype)
    experiment.configure_traits()

def profile_experiment(etype):
    from cns import TEMP_ROOT
    import cProfile
    profile_data_file = join(TEMP_ROOT, 'profile.dmp')
    cProfile.run('test_experiment("%s")' % etype, profile_data_file)
    import pstats
    p = pstats.Stats(profile_data_file)
    p.strip_dirs().sort_stats('cumulative').print_stats(50)

if __name__ == '__main__':
    profile_experiment(sys.argv[1])

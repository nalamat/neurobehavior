from enthought.pyface.api import error
from cns.data.ui.cohort import CohortView, CohortViewHandler, animal_editor
from cns.data import persistence
from cns.data.h5_utils import get_or_append_node
import sys
import tables
from enthought.traits.api import Any, Trait, TraitError
from enthought.traits.ui.api import View, Item

import logging
log = logging.getLogger(__name__)

from .experiment.aversive_experiment import AversiveFMExperiment
from .experiment.aversive_experiment import AversiveExperiment
from .experiment.positive_experiment import PositiveExperiment


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
            #item = info.object.selected
            item = selected
            if item.store_node._v_isopen:
                animal_node = item.store_node
            else:
                log.debug('Opening node %r for %r', item.store_node, item)
                file = tables.openFile(item.store_node_source, 'a',
                                       rootUEP=item.store_node_path)
                animal_node = file.root
            
            store_node = get_or_append_node(animal_node, 'experiments')
            try:
                paradigm = persistence.load_object(store_node, 'last_paradigm')
            except (tables.NoSuchNodeError, TraitError):
                log.debug('No prior paradigm found.  Creating new paradigm.')
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
                log.debug('Paradigm is not compatible with experiment')

    
            ui = model.edit_traits(parent=info.ui.control, kind='livemodal')
            if ui.result:
                persistence.add_or_update_object(model.paradigm, store_node,
                                                 'last_paradigm')
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
            Could not launch experiment.  This likely means that you
            forgot to turn on a piece of equipment.  Please check and ensure
            that the RX6, RZ5 and PA5 are turned on.  If you still get this
            error message, please try power-cycling the rack.  If this still
            does not fix the error, power-cycle the computer as well.  
            
            Please remember that you need to give the equipment rack a minute to
            boot up once you turn it back on before attempting to launch an
            experiment.
            """
            error(info.ui.control, str(e) + '\n\n' + dedent(mesg))

    def launch_appetitive(self, info, selected):
        self.launch_experiment(info, selected[0], PositiveExperiment)

    def launch_aversive_generic(self, info, selected):
        self.launch_experiment(info, selected[0], AversiveExperiment)

    def launch_aversive_fm(self, info, selected):
        self.launch_experiment(info, selected[0], AversiveFMExperiment)

def load_experiment_launcher():
    CohortView().configure_traits(view='detailed_view', handler=ExperimentLauncher())

def test_experiment(etype):
    import tables
    test_file = tables.openFile('test.hd5', 'w')
    experiment_map[etype](store_node=test_file.root).configure_traits()

if __name__ == '__main__':
    import sys
    test_experiment(sys.argv[1])

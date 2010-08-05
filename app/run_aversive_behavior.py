from config import settings

from cns.data.view.cohort import CohortView, CohortViewHandler
from cns.data import persistence
from cns.data.h5_utils import get_or_append_node
from cns.experiment.controller import AversiveController
from cns.experiment.experiment.aversive_experiment import AversiveExperiment
from cns.experiment.experiment.aversive_physiology_experiment import \
    AversivePhysiologyExperiment
import sys
import tables
from enthought.traits.api import Any, Trait, TraitError

import logging
log = logging.getLogger(__name__)

class ExperimentHandler(CohortViewHandler):

    last_paradigm = Trait(None, Any)

    def init(self, info):
        if not self.load_file(info):
            sys.exit()

    def object_dclicked_changed(self, info):
        if info.initialized:
            self.run_experiment(info)

    def run_experiment(self, info):
        try:
            item = info.object.selected
            if item.store_node._v_isopen:
                animal_node = item.store_node
            else:
                log.debug('Opening node %r for %r', item.store_node, item)
                file = tables.openFile(item.store_file, 'a', rootUEP=item.store_path)
                animal_node = file.root
            
            store_node = get_or_append_node(animal_node, 'experiments')
            try:
                paradigm = persistence.load_object(store_node, 'last_paradigm')
                paradigm.shock_settings.paradigm = paradigm
                print 'foo'
            except (tables.NoSuchNodeError, TraitError):
                print 'why am i not here'
                log.debug('No prior paradigm found.  Creating new paradigm.')
                paradigm = None
                
            handler = AversiveController()
            model = AversiveExperiment(store_node=store_node, animal=item)
            
            if paradigm is not None:
                log.debug('Animal does not have any prior paradigm.')
                log.debug('Using paradigm from previous animal.')
                model.paradigm = paradigm
            elif self.last_paradigm is not None:
                log.debug('Using paradigm from last time this animal was run')
                model.paradigm = self.last_paradigm

            model.edit_traits(handler=handler, parent=info.ui.control, kind='livemodal')
            
            # Check to see if a trial block was collected
            if model.trial_blocks > 0:
                persistence.add_or_update_object(model.paradigm, store_node, 'last_paradigm')
                item.processed = True
                self.last_paradigm = model.paradigm
                
            # Close the file if we opened it
            try: file.close()
            except NameError: pass
            
        except AttributeError: pass
        
def test_experiment():
    store = tables.openFile('test.h5', 'w')
    ae = AversiveExperiment(store_node=store.root)
    ae.paradigm.signal_warn.variables = ['frequency']
    ae.configure_traits()

if __name__ == '__main__':
    CohortView().configure_traits(handler=ExperimentHandler)
    #test_experiment()

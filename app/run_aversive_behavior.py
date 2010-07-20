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
                #print item.store_path, item.store_node
                file = tables.openFile(item.store_file, 'a', rootUEP=item.store_path)
                animal_node = file.root
                #print file.root._v_children
                #animal_node = file.getNode(item.store_path)
            
            store_node = get_or_append_node(animal_node, 'experiments')
            try:
                paradigm = persistence.load_object(store_node, 'last_paradigm')
                paradigm.shock_settings.paradigm = paradigm
            except (tables.NoSuchNodeError, TraitError):
                log.debug('behavior_experiments not found, creating node')
                paradigm = None
                
            handler = AversiveController()
            model = AversiveExperiment(store_node=store_node, animal=item)
            
            if paradigm is not None:
                model.paradigm = paradigm
            elif self.last_paradigm is not None:
                model.paradigm = self.last_paradigm

            model.edit_traits(handler=handler, parent=info.ui.control, kind='livemodal')
            
            # Check to see if a trial block was collected
            if model.trial_blocks > 0:
                persistence.add_or_update_object(model.paradigm, store_node, 'last_paradigm')
                item.processed = True
                self.last_paradigm = model.paradigm
                
            # Close the file if we opened it
            try:
                #file.flush()
                file.close()
            except NameError:
                pass
            
        except AttributeError: pass
        
def test_experiment():
    store = tables.openFile('test.h5', 'w')
    ae = AversiveExperiment(store_node=store.root)
    ae.paradigm.signal_warn.variables = ['frequency']
    ae.configure_traits()

if __name__ == '__main__':
    CohortView().configure_traits(handler=ExperimentHandler)
    #test_experiment()

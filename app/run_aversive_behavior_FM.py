from config import settings

from enthought.pyface.api import error
from cns.data.view.cohort import CohortView, CohortViewHandler
from cns.data import persistence
from cns.data.h5_utils import get_or_append_node
from cns.experiment.experiment.aversive_experiment_FM import AversiveExperimentFM
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
            except (tables.NoSuchNodeError, TraitError):
                log.debug('No prior paradigm found.  Creating new paradigm.')
                paradigm = None
                
            model = AversiveExperimentFM(store_node=store_node, animal=item)
            
            if paradigm is not None:
                log.debug('Using paradigm from last time this animal was run')
                model.paradigm = paradigm
            elif self.last_paradigm is not None:
                log.debug('Animal does not have any prior paradigm.')
                log.debug('Using paradigm from previous animal.')
                model.paradigm = self.last_paradigm

            model.edit_traits(parent=info.ui.control, kind='livemodal')
            
            # Check to see if a trial block was collected
            if model.trial_blocks > 0:
                persistence.add_or_update_object(model.paradigm, store_node, 'last_paradigm')
                item.processed = True
                self.last_paradigm = model.paradigm
                
            # Close the file if we opened it
            try: file.close()
            except NameError: pass
            
        except AttributeError: pass
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
        
def test_experiment():
    store = tables.openFile('test.h5', 'w')
    ae = AversiveExperiment(store_node=store.root)
    ae.paradigm.signal_warn.variables = ['frequency']
    ae.configure_traits()

if __name__ == '__main__':
    CohortView().configure_traits(handler=ExperimentHandler)
    #test_experiment()

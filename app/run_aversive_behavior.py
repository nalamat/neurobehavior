import settings

from cns.data.view.cohort import CohortView, CohortViewHandler
from cns.experiment.controller import AversiveController
from cns.experiment.experiment.aversive_experiment import AversiveExperiment
from cns.experiment.experiment.aversive_physiology_experiment import \
    AversivePhysiologyExperiment
import sys
import tables


class ExperimentHandler(CohortViewHandler):

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
                store_node = item.store_node
            else:
                file = tables.openFile(item.store_file, 'a')
                store_node = file.getNode(item.store_path)

            handler = AversiveController()
            model = AversiveExperiment(store_node=store_node)
            model.edit_traits(handler=handler)
            if model.edit_traits(handler=handler,
                                 parent=info.ui.control,
                                 kind='livemodal').result:
                item.processed = True
        except AttributeError: pass
        
def test_experiment():
    store = tables.openFile('test.h5', 'w')
    ae = AversiveExperiment(store_node=store.root)
    ae.paradigm.signal_warn.variables = ['frequency']
    ae.configure_traits()

def test_aversive_experiment():
    store = tables.openFile('test.h5', 'a')
    ae = AversivePhysiologyExperiment(store_node=store.root)
    ae.configure_traits()

if __name__ == '__main__':
    #CohortView().configure_traits(handler=ExperimentHandler)
    #test_experiment()
    #test_aversive_experiment()
    test_experiment()
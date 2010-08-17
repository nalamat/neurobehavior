from config import settings

from enthought.pyface.api import error
from cns.data.view.cohort import CohortView, CohortViewHandler
from cns.data import persistence
from cns.data.h5_utils import get_or_append_node
from cns.experiment.experiment.positive_experiment import PositiveExperiment
import sys
import tables
from enthought.traits.api import Any, Trait, TraitError

import logging
log = logging.getLogger(__name__)

def test_experiment():
    store = tables.openFile('test.h5', 'w')
    ae = PositiveExperiment(store_node=store.root)
    #ae.paradigm.signal_warn.variables = ['frequency']
    ae.configure_traits()

if __name__ == '__main__':
    #CohortView().configure_traits(handler=ExperimentHandler)
    test_experiment()

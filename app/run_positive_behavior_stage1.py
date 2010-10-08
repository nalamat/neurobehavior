from config import settings

from cns.data.h5_utils import get_or_append_node
from cns.experiment.experiment.positive_experiment_stage1 import \
    PositiveExperiment as PositiveExperimentStage1
from cns.experiment.experiment.positive_experiment import \
    PositiveExperiment as PositiveExperimentStage2

import tables

def experiment_stage1():
    store = tables.openFile('test.h5', 'w')
    ae = PositiveExperimentStage1(store_node=store.root)
    ae.configure_traits()

if __name__ == '__main__':
    experiment_stage1()

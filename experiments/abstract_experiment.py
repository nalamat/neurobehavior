from datetime import datetime

from enthought.traits.api import HasTraits, Any, Instance, Property
from enthought.traits.ui.api import View

from cns.data.h5_utils import append_date_node, append_node

from abstract_experiment_controller import AbstractExperimentController
from abstract_experiment_data import AbstractExperimentData
from abstract_experiment_paradigm import AbstractExperimentParadigm

class AbstractExperiment(HasTraits):

    animal      = Any
    store_node  = Any
    exp_node    = Any
    data_node   = Any

    data        = Instance(AbstractExperimentData, store='node')
    paradigm    = Instance(AbstractExperimentParadigm, store='node')

    start_time  = Instance(datetime, store='attribute')
    stop_time   = Instance(datetime, store='attribute')
    duration    = Property(store='attribute')

    def _store_node_changed(self, new):
        self.exp_node = append_date_node(new)
        self.data_node = append_node(self.exp_node, 'data')

    def __init__(self, **kwargs):
        super(AbstractExperiment, self).__init__(**kwargs)

    def _get_date(self):
        return self.start_time.date()

    def _get_duration(self):
        if self.stop_time is None and self.start_time is None:
            return datetime.timedelta()
        elif self.stop_time is None:
            return datetime.now()-self.start_time
        else:
            return self.stop_time-self.start_time

    traits_view = View(handler=AbstractExperimentController)

from datetime import datetime

from enthought.traits.api import HasTraits, Any, Instance, Property
from enthought.traits.ui.api import View

from abstract_experiment_controller import AbstractExperimentController
from abstract_experiment_data import AbstractExperimentData
from abstract_experiment_paradigm import AbstractExperimentParadigm

class AbstractExperiment(HasTraits):

    animal      = Any
    store_node  = Any
    data        = Instance(AbstractExperimentData)
    paradigm    = Instance(AbstractExperimentParadigm)

    start_time  = Instance(datetime, store='attribute')
    stop_time   = Instance(datetime, store='attribute')
    duration    = Property(store='attribute')

    def _get_date(self):
        return self.start_time.date()

    def _get_duration(self):
        if self.stop_time is None and self.start_time is None:
            return timedelta()
        elif self.stop_time is None:
            return datetime.now()-self.start_time
        else:
            return self.stop_time-self.start_time

    traits_view = View(handler=AbstractExperimentController)

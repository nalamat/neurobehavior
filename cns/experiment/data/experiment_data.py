from enthought.traits.api import HasTraits, Instance, Property
from datetime import datetime, timedelta

class ExperimentData(HasTraits):

    start_time = Instance(datetime, store='attribute')
    stop_time = Instance(datetime, store='attribute')
    duration = Property(store='attribute')

    def _get_date(self):
        return self.start_time.date()

    def _get_duration(self):
        if self.stop_time is None and self.start_time is None:
            return timedelta()
        elif self.stop_time is None:
            return datetime.now()-self.start_time
        else:
            return self.stop_time-self.start_time

class AnalyzedData(HasTraits):
    pass

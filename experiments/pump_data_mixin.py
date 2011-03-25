from enthought.traits.api import HasTraits, List, Property, Float

WATER_DTYPE = [('timestamp', 'i'), ('infused', 'f')]

class PumpDataMixin(HasTraits):

    PUMP_DATA_VERSION = Float(1.0)

    water_log = List(store='table', dtype=WATER_DTYPE)
    water_infused = Property(Float, depends_on='water_log')

    def _get_water_infused(self):
        try:
            return self.water_log[-1][1]
        except:
            return 0

    def log_water(self, ts, infused):
        self.water_log.append((ts, infused))

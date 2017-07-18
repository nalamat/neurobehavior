from traits.api import HasTraits, Float, Any
import numpy as np

class PumpDataMixin(HasTraits):

    PUMP_DATA_VERSION = Float(2.0)
    
    water_log = Any
    water_infused = Float

    def _water_log_default(self):
        file = self.store_node._v_file
        description = np.dtype([('timestamp', 'i'), ('infused', 'f')])
        node = file.createTable(self.store_node, 'water_log', description)
        node.append([(0, 0)])
        return node

    def log_water(self, ts, infused):
        # The append() method of a tables.Table class requires a list of rows
        # (i.e. records) to append to the table.  Since we only append a single
        # row at a time, we need to nest it as a list that contains a single
        # record.
        self.water_log.append([(ts, infused)])
        self.water_infused = infused

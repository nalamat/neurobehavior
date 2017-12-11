import logging
import numpy as np
from traits.api import HasTraits, Float, Any, Instance
from cns.channel import Channel, FileChannel, FileEpoch
from cns.data.h5_utils import get_or_append_node

log = logging.getLogger(__name__)

class PumpDataMixin(HasTraits):

    PUMP_DATA_VERSION = Float(2.0)

    water_infused = Float
    water_log     = Any
    epoch_node    = Any
    pump_epoch    = Instance(FileEpoch)

    def setup(self):
        self.pump_epoch._buffer

    def _water_log_default(self):
        file = self.store_node._v_file
        description = np.dtype([('timestamp', 'f'), ('infused', 'f')])
        node = file.createTable(self.store_node, 'water_log', description)
        node.append([(0, 0)])
        return node

    def _epoch_node_default(self):
        return get_or_append_node(self.store_node, 'epoch')

    def _pump_epoch_default(self):
        log.debug('Creating epoch node "pump" in HDF5')
        return FileEpoch(node=self.epoch_node, name='pump'  , fs=1, dtype=np.float32)

    def log_water(self, ts, infused):
        # The append() method of a tables.Table class requires a list of rows
        # (i.e. records) to append to the table.  Since we only append a single
        # row at a time, we need to nest it as a list that contains a single
        # record.
        self.water_log.append([(ts, infused)])
        self.water_infused = infused

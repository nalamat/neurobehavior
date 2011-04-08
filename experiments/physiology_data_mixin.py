from enthought.traits.api import HasTraits, Instance
from cns.channel import FileMultiChannel, RAMMultiChannel, FileChannel
from cns.data.h5_utils import get_or_append_node
import numpy as np

class PhysiologyDataMixin(HasTraits):

    # This stores a copy of the most recent data in computer memory for quick
    # access by the plotting functions.  This will *not* be saved in the HDF5
    # file.
    physiology_ram = Instance(RAMMultiChannel)

    # These are the actual data stores
    physiology_raw = Instance(FileMultiChannel, store='channel',
            store_path='physiology/raw')

    # These are the actual data stores
    physiology_processed = Instance(FileMultiChannel, store='channel',
            store_path='physiology/processed')

    # The array of timestamps corresponding to stimulus onset
    #physiology_ts = Instance(FileChannel, store='channel',
            #store_path='physiology/ts')

    physiology_ts = Instance('cns.channel.Timeseries', ())

    def _physiology_ram_default(self):
        return RAMMultiChannel(channels=16, fs=25e3, window=5)

    def _physiology_raw_default(self):
        physiology_node = get_or_append_node(self.store_node, 'physiology')
        return FileMultiChannel(node=physiology_node, channels=16, name='raw',
                dtype=np.float32)

    def _physiology_processed_default(self):
        physiology_node = get_or_append_node(self.store_node, 'physiology')
        return FileMultiChannel(node=physiology_node, channels=16,
                name='processed', dtype=np.float32)

    #def _physiology_ts_default(self):
    #    physiology_node = get_or_append_node(self.store_node, 'physiology')
    #    return FileChannel(node=physiology_node, channels=1, name='ts',
    #            dtype=np.int32)

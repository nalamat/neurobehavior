from cns import get_config
from enthought.traits.api import HasTraits, Instance, List, Any
from cns.channel import (FileMultiChannel, RAMMultiChannel, FileChannel,
        FileSnippetChannel)
from cns.data.h5_utils import get_or_append_node
import numpy as np

CHANNELS = get_config('PHYSIOLOGY_CHANNELS')

class PhysiologyData(HasTraits):

    store_node = Any

    # This stores a copy of the most recent data in computer memory for quick
    # access by the plotting functions.  This will *not* be saved in the HDF5
    # file.
    physiology_ram = Instance(RAMMultiChannel)

    # Raw physiology data
    physiology_raw = Instance(FileMultiChannel, store='channel',
            store_path='physiology/raw')
    # Data after it has been referenced to a differential and band-pass filtered
    physiology_processed = Instance(FileMultiChannel, store='channel',
            store_path='physiology/processed')
    # TTL indicating whether
    physiology_sweep = Instance(FileChannel, store='channel',
            store_path='physiology/sweep')

    physiology_ts = Instance('cns.channel.Timeseries', ())

    physiology_spikes = List(Instance(FileSnippetChannel))

    def _physiology_spikes_default(self):
        #physiology_node = get_or_append_node(self.store_node, 'physiology')
        channels = []
        for i in range(CHANNELS):
            name = 'spike_{:02}'.format(i+1)
            channel = FileSnippetChannel(node=self.store_node, name=name,
                    dtype=np.float32, snippet_size=38)
            channels.append(channel)
        return channels

    def _physiology_sweep_default(self):
        #physiology_node = get_or_append_node(self.store_node, 'physiology')
        return FileChannel(node=self.store_node, name='sweep', dtype=np.bool)

    def _physiology_ram_default(self):
        return RAMMultiChannel(channels=CHANNELS, fs=25e3, window=5)

    def _physiology_raw_default(self):
        #physiology_node = get_or_append_node(self.store_node, 'physiology')
        return FileMultiChannel(node=self.store_node, channels=CHANNELS,
                name='raw', dtype=np.float32)

    def _physiology_processed_default(self):
        #physiology_node = get_or_append_node(self.store_node, 'physiology')
        return FileMultiChannel(node=self.store_node, channels=CHANNELS,
                name='processed', dtype=np.float32)

from cns import get_config
from enthought.traits.api import HasTraits, Instance, List, Any
from cns.channel import (FileMultiChannel, FileChannel, FileSnippetChannel)
from cns.data.h5_utils import get_or_append_node
import numpy as np

CHANNELS = get_config('PHYSIOLOGY_CHANNELS')

class PhysiologyData(HasTraits):

    store_node = Any

    # Raw physiology data
    raw = Instance(FileMultiChannel, store='channel')
    # Data after it has been referenced to a differential and band-pass filtered
    processed = Instance(FileMultiChannel, store='channel')
    sweep = Instance(FileChannel, store='channel')
    ts = Instance('cns.channel.Timeseries', ())
    spikes = List(Instance(FileSnippetChannel))

    def _spikes_default(self):
        channels = []
        node = self.store_node
        for i in range(CHANNELS):
            name = 'spike_{:02}'.format(i+1)
            ch = FileSnippetChannel(node=node, name=name, dtype=np.float32,
                                    snippet_size=18)
            channels.append(ch)
        return channels

    def _sweep_default(self):
        return FileChannel(node=self.store_node, name='sweep', dtype=np.bool)

    def _raw_default(self):
        return FileMultiChannel(node=self.store_node, channels=CHANNELS,
                name='raw', dtype=np.float32)

    def _processed_default(self):
        return FileMultiChannel(node=self.store_node, channels=CHANNELS,
                name='processed', dtype=np.float32)

    #def _ts_default(self):
    #    return Timeseries(node=self.store_node, name='ts')


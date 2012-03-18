import tables
from tempfile import mkdtemp
from os import path
from cns import get_config
from enthought.traits.api import HasTraits, Instance, List, Any
from cns.channel import (FileMultiChannel, FileChannel, FileSnippetChannel,
                         FileTimeseries, FileEpoch)
import numpy as np

CHANNELS = get_config('PHYSIOLOGY_CHANNELS')
SNIPPET_SIZE = get_config('PHYSIOLOGY_SPIKE_SNIPPET_SIZE')

class PhysiologyData(HasTraits):

    store_node = Any

    #############################################################################
    # Permanent data
    #############################################################################
    # Raw (permanent) physiology data that will be stored in the data file that
    # is retained at the end of the experiment.

    raw         = Instance(FileMultiChannel)
    sweep       = Instance(FileChannel)
    ts          = Instance(FileTimeseries)
    epoch       = Instance(FileEpoch)

    def _sweep_default(self):
        return FileChannel(node=self.store_node, name='sweep', dtype=np.bool,
                           use_checksum=True)

    def _raw_default(self):
        return FileMultiChannel(node=self.store_node, channels=CHANNELS,
                                name='raw', dtype=np.float32,
                                compression_type='lzo', compression_level=1,
                                use_shuffle=True, use_checksum=True)

    def _ts_default(self):
        return FileTimeseries(node=self.store_node, name='ts', dtype=np.int32,
                              use_checksum=True)

    def _epoch_default(self):
        return FileEpoch(node=self.store_node, name='epoch', dtype=np.int32)

    #############################################################################
    # TEMPORARY DATA
    #############################################################################
    # Temporary data for plotting.  Stored in a temporary file that will
    # eventually be discarded at the end of the experiment.

    # Where to store the temporary data
    temp_node   = Any
    processed   = Instance(FileMultiChannel)
    spikes      = List(Instance(FileSnippetChannel))

    def _temp_node_default(self):
        filename = path.join(mkdtemp(), 'processed_physiology.h5')
        tempfile = tables.openFile(filename, 'w')
        return tempfile.root

    def _processed_default(self):
        return FileMultiChannel(node=self.temp_node, channels=CHANNELS,
                                name='processed', dtype=np.float32)

    def _spikes_default(self):
        channels = []
        for i in range(CHANNELS):
            name = 'spike_{:02}'.format(i+1)
            ch = FileSnippetChannel(node=self.temp_node, name=name,
                    dtype=np.float32, snippet_size=SNIPPET_SIZE)
            channels.append(ch)
        return channels

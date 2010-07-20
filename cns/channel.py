#------------------------------------------------------------------------------
#
#  Copyright (c) 2010, Brad N. Buran
#  All rights reserved.
#
#  Author:        Brad N. Buran
#  Original Date: 06/28/2010
#
#------------------------------------------------------------------------------

from cns.buffer import SoftwareRingBuffer
from cns.data.h5_utils import append_node
from cns.util.signal import rfft
from enthought.traits.api import HasTraits, Property, Array, Int, Event, \
    Instance, on_trait_change, Bool, Any, String, Float, cached_property, List, Str, \
    DelegatesTo, Enum
import numpy as np
import tables

class AbstractChannel(HasTraits):

    def to_index(self, time):
        return int((time-self.t0)*self.fs)

    def get_indices(self, *args):
        return [self.get_index(a) for a in args]

    def get_range(self, start, end, reference=None):
        if reference is not None:
            if len(self.trigger_indices):
                ref_idx = self.trigger_indices[reference]
            else:
                return self.signal[0:0], 0, 0
        else:
            ref_idx = 0
        lb = max(0, self.to_index(start)+ref_idx)
        ub = max(0, self.to_index(end)+ref_idx)
        signal = self.signal[lb:ub]
        lb_time = lb/self.fs + self.t0 - ref_idx/self.fs
        ub_time = lb_time + len(signal)/self.fs
        return signal, lb_time, ub_time

    def get_recent_range(self, start, end=0):
        lb = min(-1, int(start*self.fs))
        ub = min(-1, int(end*self.fs))
        signal = self.signal[lb:ub]
        ub_time = ub/self.fs
        lb_time = ub_time-len(signal)/self.fs
        return signal, lb_time, ub_time

    def filter(self, filter):
        '''Takes b,a parameters for filter'''
        self.signal = filtfilt(self.signal, **filter)

class Channel(AbstractChannel):

    fs = Float                          # Sampling frequency
    t0 = Float(0)                       # Time of first sample (typically zero)
    trigger_indices = List([])

    updated = Event
    signal = Property

    def _get_signal(self):
        raise NotImplementedError, 'Use a subclass of Channel'

class FileChannel(Channel):

    # Default settings for the filter should create the smallest possible file
    # size while providing adequate read/write performance.  Checksumming allows
    # us to check for data integrity.  I have it disabled by default because
    # small aberrations in a large, continuous waveform are not of as much
    # concern to us and I understand there can be a sizable performance
    # penalty.
    compression_level = Int(1)
    compression_type = Enum('zlib', 'lzo', 'bzip')
    use_checksum = Bool(False)
    
    # It is important to implement dtype appropriately, otherwise it defaults
    # to float64 (double-precision float).
    #dtype = Instance(type) # TODO: How do we restrict this to a dtype?
    dtype = Any

    node = Instance(tables.group.Group)
    name = String('FileChannel')
    expected_duration = Float(60) # seconds
    shape = Property
    
    buffer = Instance(tables.array.Array)

    def _get_shape(self):
        return (0,)

    def _create_buffer(self):
        atom = tables.Atom.from_dtype(np.dtype(self.dtype))
        filters = tables.Filters(complevel=self.compression_level,
                                 complib=self.compression_type,
                                 fletcher32=self.use_checksum)

        buffer = append_node(self.node, self.name, 'EArray', atom, self.shape,
                             expectedrows=int(self.fs*self.expected_duration),
                             filters=filters)

        buffer.setAttr('fs', self.fs)
        return buffer

    def _buffer_default(self):
        return self._create_buffer()

    def _get_signal(self):
        return self.buffer

    def send(self, data):
        self.buffer.append(data)
        self.updated = True

class RAMChannel(Channel):

    window = Float(10)
    samples = Property(Int, depends_on='window, fs')

    buffer = Array
    offset = Int(0)
    dropped = Int(0)

    partial_idx = 0

    t0 = Property(depends_on="offset, fs")

    @cached_property
    def _get_t0(self):
        return self.offset/self.fs

    @cached_property
    def _get_samples(self):
        return int(self.window * self.fs)

    def _buffer_default(self):
        return np.empty(self.samples)

    def _get_signal(self):
        return self.buffer

    def send(self, data):
        self._write(data)
        self.updated = True

    def _partial_write(self, data):
        size = len(data)
        if size > self.samples:
            self.buffer = data[-self.samples:]
            self.dropped = size-self.samples
            self.offset = size-self.samples
            self._write = self._full_write
        elif self.partial_idx+size > self.samples:
            overflow = (self.partial_idx+size)-self.samples
            remainder = size-overflow
            self.buffer[self.partial_idx:] = data[:remainder]
            del self.partial_idx
            self._write = self._full_write
            self._write(data[-overflow:])
        else:
            self.buffer[self.partial_idx:self.partial_idx+size] = data
            self.partial_idx += size

    def _full_write(self, data):
        size = len(data)
        if size > self.samples:
            self.buffer = data[-self.samples:]
            self.dropped += size-self.samples
            self.offset += size-self.samples
        else:
            # Shift elements at end of buffer to beginning so we can write new data.  Old data at beginning is discarded.  If old data is discarded, we update offset.
            remainder = self.samples-size
            if remainder:
                self.buffer[:remainder] = self.buffer[-remainder:]
                self.offset += size
            # Write new data to end of buffer
            self.buffer[-size:] = data

    _write = _partial_write

class BufferedChannel(Channel):

    window = Float(10)
    samples = Property(Int, depends_on='window, fs')
    buffer = Instance(SoftwareRingBuffer)

    @cached_property
    def _get_samples(self):
        return int(self.window * self.fs)

    #signal = Property(Array(dtype='f'))

    def _buffer_default(self):
        return SoftwareRingBuffer(self.samples)

    def _get_signal(self):
        return self.buffer.data

    def send(self, data):
        if len(data):
            self.buffer.write(data)
            self.updated = True

class StaticChannel(Channel):

    _signal = Array(dtype='f')

    def _get_signal(self):
        return self._signal

    def _set_signal(self, signal):
        self._signal = signal

class MultiChannel(Channel):

    channels = Int(8)
    names = List(Str)

    def get_channel(self, channel):
        try:
            idx = self.names.index(channel)
        except ValueError:
            idx = channel
        #channel = DerivedChannel(parent=self, idx=idx)
        #channel.sync_trait('fs', self)
        #channel.sync_trait('t0', self)
        #channel.sync_trait('updated', self)
        #channel.sync_trait('trigger_indices', self)
        #return channel
        return DerivedChannel(parent=self, idx=idx)

class DerivedChannel(AbstractChannel):
    '''This is a hack, but I'm not sure the best way around this.'''

    parent = Instance(MultiChannel)
    _ = DelegatesTo('parent')
    signal = Property

    def _get_signal(self):
        return self.parent.signal[:,self.idx]

class RAMMultiChannel(RAMChannel, MultiChannel):

    def _buffer_default(self):
        return np.empty((self.samples, self.channels))

class BufferedMultiChannel(BufferedChannel, MultiChannel):

    def _buffer_default(self):
        return SoftwareRingBuffer((self.samples, self.channels))

class FileMultiChannel(FileChannel, MultiChannel):

    channels = Int(8)
    name = 'FileMultiChannel'

    def _get_shape(self):
        return (0, self.channels)

    def _create_buffer(self):
        buffer = super(FileMultiChannel, self)._create_buffer()
        buffer.setAttr('channels', self.channels)
        buffer.setAttr('names', self.names)
        return buffer

class SnippetChannel(Channel):

    buffer = Instance(SoftwareRingBuffer)
    samples = Int
    history = Int
    signal = Property(Array(dtype='f'))
    average_signal = Property(Array(dtype='f'))
    buffered = Int(0)
    buffer_full = Bool(False)

    @on_trait_change('samples, fs, history')
    def _configure_buffer(self):
        self.buffer = SoftwareRingBuffer((self.history, self.samples))

    def _get_t(self):
        return np.arange(-self.samples, 0) / self.fs

    def _get_signal(self):
        return self.buffer.buffered

    def send(self, data):
        # Ensure that 1D arrays containing a single snippet are broadcast
        # properly to the correct shape.
        data.shape = (-1, self.samples)
        added = self.buffer.write(data)

        if self.buffer_full:
            self.updated = added, added
        else:
            self.buffered += added
            if self.buffered > self.history:
                self.buffer_full = True
                removed = self.buffered % self.history
                self.buffer_full
                self.updated = removed, added
            else:
                self.updated = 0, added

    def _get_average_signal(self):
        return self.buffer.buffered.mean(0)

    def __len__(self):
        return self.samples

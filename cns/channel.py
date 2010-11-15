#------------------------------------------------------------------------------
#
#  Copyright (c) 2010, Brad N. Buran
#  All rights reserved.
#
#  Author:        Brad N. Buran
#  Original Date: 06/28/2010
#
#------------------------------------------------------------------------------

import warnings
from cns.buffer import SoftwareRingBuffer
from cns.data.h5_utils import append_node
from cns.util.signal import rfft
from enthought.traits.api import HasTraits, Property, Array, Int, Event, \
    Instance, on_trait_change, Bool, Any, String, Float, cached_property, List, Str, \
    DelegatesTo, Enum
import numpy as np
import tables

import logging
log = logging.getLogger(__name__)

class AbstractChannel(HasTraits):
    '''
    Base class for dealing with a continuous stream of data.  Facilitates
    extracting a segment of the waveform (for analysis or plotting)
    :func:`get_range` and :func:`get_recent_range`.

    fs
        Sampling frequency (number of samples per second)
    t0
        Time offset (i.e. time of first sample) relative to the start of
        acquisition.  This typically defaults to zero; however, some subclasses
        may discard old data (e.g.  :class:`RAMChannel`), so we need to factor
        in the time offset when attempting to extract a given segment of the
        waveform for analysis.  

    trigger_indices
        Indices of triggers relative to the start of acquisition.  Eventually I
        want to split this out of the class and simply provide the value to
        :func:`get_range` that way we can select which trigger we want to
        reference the data to.
    '''

    def to_index(self, time):
        '''Convert time to the corresponding index in the waveform.  Note that
        the index may be negative if the time is less than t0.  Since Numpy
        allows negative indices, be sure to check the value.
        '''
        return int((time-self.t0)*self.fs)

    def to_samples(self, time):
        return int(time*self.fs)

    def get_range_index(self, start, end, reference=0):
        '''
        Returns a subset of the range specified in samples

        The samples must be speficied relative to start of data acquisition.

        Parameters
        ----------
        start : num samples (int)
            Start index in samples
        end : num samples (int)
            End index in samples
        reference : num samples (int), optional
            Time of trigger to reference start and end to
        '''
        t0_index = int(self.t0*self.fs)
        lb = max(0, start-t0_index+reference)
        ub = max(0, end-t0_index+reference)
        log.debug('Signal shape %r', self.signal.shape)
        return self.signal[..., lb:ub]

    def get_index(self, index, reference=0):
        t0_index = int(self.t0*self.fs)
        index = max(0, index-t0_index+reference)
        return self.signal[..., index]

    def get_range(self, start, end, reference=None):
        '''
        Returns a subset of the range.

        Parameters
        ----------
        start : float, sec
            Start time.
        end : float, sec
            End time.
        reference : int, optional
            Trigger index to reference to.  If None, start is referenced to
            start of data acquisition.  If -1, start is referenced to the time
            of the most recent trigger.

        Note: Eventually reference will be deprecated in favor of passing the
        actual trigger time.  Right now we can associate only a single set of
        triggers with a channel!
        '''
        log.debug('Range (%.2f, %.2f)', lb, ub)

        if reference is not None:
            if len(self.trigger_indices):
                ref_idx = self.trigger_indices[reference]
            else:
                return self.signal[..., 0:0], 0, 0
        else:
            ref_idx = 0
        lb = max(0, self.to_index(start)+ref_idx)
        ub = max(0, self.to_index(end)+ref_idx)
        log.debug('Range index (%d, %d)', lb, ub)
        log.debug('Signal size %r', self.signal.shape)
        signal = self.signal[..., lb:ub]
        lb_time = lb/self.fs + self.t0 - ref_idx/self.fs
        ub_time = lb_time + len(signal)/self.fs
        return signal, lb_time, ub_time

    def get_recent_range(self, start, end=0):
        '''
        Returns a subset of the range, with start and end referenced to the most
        recent sample.

        Parameters
        ==========
        start
            Start time
        end
            End time
        '''
        
        lb = min(-1, int(start*self.fs))
        ub = min(-1, int(end*self.fs))
        # This check is necessary to avoid raising an error in the HDF5
        # (PyTables?) library if it attempts to slice an empty array.
        if len(self.signal) == 0:
            signal = np.array([])
        else:
            signal = self.signal[..., lb:ub]
        ub_time = ub/self.fs
        lb_time = ub_time-signal.shape[-1]/self.fs
        return signal, lb_time, ub_time

    def filter(self, filter):
        raise NotImplementedException
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
    '''
    An implementation of `Channel` that streams acquired data to a HDF5_ EArray.
    Note that if no buffer is availale, then one will be created automatically.

    .. _HDF5: http://www.hdfgroup.org/HDF5/

    Properties
    ==========
    dtype
        Default is float64.  It is a good idea to set dtype appropriately for
        the waveform (e.g. use bool for TTL data) to minimize file size.  Note
        that Matlab does not currently support the HDF5 BITFIELD (e.g. boolean)
        type and will be unable to read waveforms stored in this format.
    node
        A HDF5 node that the array should be added to
    name
        Name of the array
    expected_duration
        Rough estimate of how long the waveform will be.  This is used (in
        conjunction with fs) to optimize the "chunksize" when creating the
        array.

    Compression properties
    ======================
    compression_level
        Between 0 and 9, with 0=uncompressed and 9=maximum
    compression_type
        zlib, lzo or bzip
    use_checksum
        Ensures data integrity, but at cost of degraded read/write performance

    Default settings for the compression filter should create the smallest
    possible file size while providing adequate read/write performance.
    Checksumming allows us to check for data integrity.  I have it disabled by
    default because small aberrations in a large, continuous waveform are not of
    as much concern to us and I understand there can be a sizable performance
    penalty.
    
    Note that if compression_level is > 0 and compression_type is None,
    tables.Filter will raise an exception.
    '''
    compression_level = Int(1)
    compression_type = Enum('zlib', 'lzo', 'bzip', None)
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

    def _buffer_default(self):
        atom = tables.Atom.from_dtype(np.dtype(self.dtype))
        filters = tables.Filters(complevel=self.compression_level,
                                 complib=self.compression_type,
                                 fletcher32=self.use_checksum)
        buffer = append_node(self.node, self.name, 'EArray', atom, self.shape,
                             expectedrows=int(self.fs*self.expected_duration),
                             filters=filters)
        buffer.setAttr('fs', self.fs)
        return buffer

    def _get_signal(self):
        return self.buffer

    def send(self, data):
        self.buffer.append(data)
        self.updated = True

    def write(self, data):
        self.send(data)

class RAMChannel(Channel):
    '''Buffers data in memory without saving it to disk.

    Uses a ringbuffer algorithm designed for efficient reads (writes are not as
    efficient, but should still be fairly quick).  The assumption is that this
    is used for plotting data, and reads will be more common than writes (due to
    panning, zooming and scaling).

    Parameters
    ==========
    window
        Number of seconds to buffer
    '''

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
        size = data.shape[-1]
        if size > self.samples:
            self.buffer = data[..., -self.samples:]
            self.dropped = size-self.samples
            self.offset = size-self.samples
            self._write = self._full_write
        elif self.partial_idx+size > self.samples:
            overflow = (self.partial_idx+size)-self.samples
            remainder = size-overflow
            self.buffer[... ,self.partial_idx:] = data[..., :remainder]
            del self.partial_idx
            self._write = self._full_write
            self._write(data[..., -overflow:])
        else:
            self.buffer[..., self.partial_idx:self.partial_idx+size] = data
            self.partial_idx += size

    def _full_write(self, data):
        #size = len(data)
        size = data.shape[-1]
        if size > self.samples:
            self.buffer = data[..., -self.samples:]
            self.dropped += size-self.samples
            self.offset += size-self.samples
        else:
            # Shift elements at end of buffer to beginning so we can write new
            # data.  Old data at beginning is discarded.  If old data is
            # discarded, we update offset.
            remainder = self.samples-size
            if remainder:
                self.buffer[..., :remainder] = self.buffer[..., -remainder:]
                self.offset += size
            # Write new data to end of buffer
            self.buffer[..., -size:] = data

    _write = _partial_write

class BufferedChannel(Channel):

    window = Float(10)
    samples = Property(Int, depends_on='window, fs')
    buffer = Instance(SoftwareRingBuffer)

    @cached_property
    def _get_samples(self):
        return int(self.window * self.fs)

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
    #names = List(Str)

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
        return np.empty((self.channels, self.samples))

class BufferedMultiChannel(BufferedChannel, MultiChannel):

    def _buffer_default(self):
        return SoftwareRingBuffer((self.channels, self.samples))

class FileMultiChannel(FileChannel, MultiChannel):

    channels = Int(8)
    name = 'FileMultiChannel'

    def _get_shape(self):
        return (self.channels, 0)

    def _buffer_default(self):
        buffer = super(FileMultiChannel, self)._buffer_default()
        buffer.setAttr('channels', self.channels)
        #buffer.setAttr('names', self.names)
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

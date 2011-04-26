'''
:mod:`cns.channel` -- Containers for timeseries data
====================================================

.. module:: cns.channel
    :platform: Unix, Windows, OSX
    :synopsis: Provides containers for timeseries data
.. moduleauthor:: Brad Buran <bburan@alum.mit.edu>
'''

import warnings
from cns.buffer import SoftwareRingBuffer
from cns.data.h5_utils import append_node
from cns.util.signal import rfft
from enthought.traits.api import HasTraits, Property, Array, Int, Event, \
    Instance, on_trait_change, Bool, Any, String, Float, cached_property, List, Str, \
    DelegatesTo, Enum, Dict
import numpy as np
import tables

import logging
log = logging.getLogger(__name__)

class Timeseries(HasTraits):

    updated = Event
    fs = Float
    t0 = Float(0)

    buffer = List([])

    def send(self, timestamps):
        #timestamps = np.array(timestamps)/self.fs
        self.buffer.extend(timestamps.ravel())
        self.updated = timestamps

    def get_range(self, lb, ub):
        timestamps = np.array(self.buffer)/self.fs 
        mask = (timestamps>=lb)&(timestamps<ub)
        return timestamps[mask]

    #def latest(self):
    #    if self.get_size() > 0:
    #        return self.signal[-1]/self.fs
    #    else:
    #        return self.t0

    def latest(self):
        if len(self.buffer) > 0:
            return self.buffer[-1]/self.fs
        else:
            return self.t0

class Channel(HasTraits):
    '''
    Base class for dealing with a continuous stream of data.  Subclasses are
    responsible for implementing the data buffer (e.g. either a file-based or
    memory-based buffer).

    fs
        Sampling frequency (number of samples per second)
    t0
        Time offset (i.e. time of first sample) relative to the start of
        acquisition.  This typically defaults to zero; however, some subclasses
        may discard old data (e.g.  :class:`RAMChannel`), so we need to factor
        in the time offset when attempting to extract a given segment of the
        waveform for analysis.  
    signal
        The sample sequence
    '''

    metadata = Dict({'selections': None})

    # Sampling frequency of the data stored in the buffer
    fs = Float

    # Time of first sample in the buffer.  Typically this is 0, but if we delay
    # acquisition or discard "old" data (e.g. via a RAMBuffer), then we need to
    # update t0.
    t0 = Float(0)

    # Fired when new data is added
    updated = Event
   
    signal = Property

    def get_data(self):
        return self.signal

    def _get_signal(self):
        raise NotImplementedError, 'Use a subclass of Channel'

    def to_index(self, time):
        '''
        Convert time to the corresponding index in the waveform.  Note that the
        index may be negative if the time is less than t0.  Since Numpy allows
        negative indices, be sure to check the value.
        '''
        return int((time-self.t0)*self.fs)

    def to_samples(self, time):
        '''
        Convert time to number of samples.
        '''
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
        #lb = np.max(0, start-t0_index+reference)
        #ub = np.max(0, end-t0_index+reference)
        lb = start-t0_index+reference
        ub = end-t0_index+reference
        if np.iterable(lb):
            return [self.signal[lb:ub] for lb, ub in zip(lb, ub)]
        else:
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
        reference : float, optional
            Set to -1 to get the most recent range
        '''
        # Return an empty array of the appropriate dimensionality (whether it's
        # single or multichannel)
        if start == end:
            return self.signal[..., 0:0]

        # Otherwise, ensure that start time is greater than end 
        if start > end:
            raise ValueError("Start time must be < end time")

        if reference is not None:
            if reference == -1:
                return self.get_recent_range(start, end)
            else:
                ref_idx = self.to_index(reference)
        else:
            ref_idx = 0

        # Due to the two checks at the beginning of this function, we do not
        # need to worry about start == inf and end == -inf
        if start == -np.inf:
            lb = self.t0
        else:
            lb = max(0, self.to_index(start)+ref_idx)
        if end == np.inf:
            ub = self.get_size()
        else:
            ub = max(0, self.to_index(end)+ref_idx)

        return self.signal[..., lb:ub]

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

    def get_size(self):
        return self.signal.shape[-1]

    def get_bounds(self):
        '''
        Returns valid range of times as a tuple (lb, ub)
        '''
        return self.t0, self.t0 + self.get_size()/self.fs

    def latest(self):
        if self.get_size() > 0:
            return self.signal[-1]/self.fs
        else:
            return self.t0

    def send(self, data):
        '''
        Convenience method that allows us to use a Channel as a "sink" for a
        processing pipeline.
        '''
        self.write(data)

    def write(self, data):
        '''
        Write data to buffer.
        '''
        lb = self.get_size()
        self._write(data)
        ub = self.get_size()

        # Updated has the upper and lower bound of the data that was added.
        # Some plots will use this to determine whether the updated region of
        # the data is within the visible region.  If not, no update is made.
        self.updated = lb/self.fs, ub/self.fs

    def summarize(self, timestamps, offset, duration, fun):
        if len(timestamps) == 0:
            return np.array([])

        # Channel.to_samples(time) converts time (in seconds) to the
        # corresponding number of samples given the sampling frequency of the
        # channel.  If the trial begins at sample n, then we want to analyze
        # contact during the interval [n+lb_index, n+ub_index).
        lb_index = self.to_samples(offset)
        ub_index = self.to_samples(offset+duration)
        result = []

        # Variable ts is the sample number at which the trial began and is a
        # multiple of the contact sampling frequency.
        # Channel.get_range_index(lb_sample, ub_sample, reference_sample)
        # will return the specified range relative to the reference sample.
        # Since we are interested in extracting the range [contact_offset,
        # contact_offset+contact_dur) relative to the timestamp, we need to
        # first convert the range to the number of samples (which we did
        # above where we have it as [lb_index, ub_index)).  Since our
        # reference index (the timestamp) is already in the correct units,
        # we don't need to convert it.
        if np.iterable(timestamps):
            range = self.get_range_index(lb_index, ub_index, timestamps)
            return np.array([fun(r) for r in range])
            #for ts in timestamps:
            #    range = self.get_range_index(lb_index, ub_index, ts)
            #    result.append(fun(range))
            #return np.array(result)
        else:
            range = self.get_range_index(lb_index, ub_index, timestamps)
            return fun(range)

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
        A HDF5 node that will host the array
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
    compression_level   = Int(9)
    compression_type    = Enum('zlib', 'lzo', 'bzip', 'blosc', None)
    use_checksum        = Bool(False)
    
    # It is important to implement dtype appropriately, otherwise it defaults to
    # float64 (double-precision float).
    dtype = Any

    node                = Instance(tables.group.Group)
    name                = String('FileChannel')
    expected_duration   = Float(1800) # seconds
    shape               = Property
    buffer              = Instance(tables.array.Array)

    def _get_shape(self):
        return (0,)

    def _buffer_default(self):
        atom = tables.Atom.from_dtype(np.dtype(self.dtype))
        filters = tables.Filters(complevel=self.compression_level,
                complib=self.compression_type, fletcher32=self.use_checksum)
        buffer = append_node(self.node, self.name, 'EArray', atom, self.shape,
                expectedrows=int(self.fs*self.expected_duration),
                filters=filters)
        return buffer

    #@on_trait_change('fs')
    def _fs_changed(self, new):
        self.buffer.setAttr('fs', self.fs)

    def _get_signal(self):
        return self.buffer

    def _write(self, data):
        if data.ndim != 1 and data.shape[0] != 1:
            raise ValueError, "First dimension must be 1"
        self.buffer.append(data.ravel())

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

    window  = Float(10)
    samples = Property(Int, depends_on='window, fs')
    t0      = Property(depends_on="offset, fs")

    buffer = Array
    offset = Int(0)
    dropped = Int(0)

    partial_idx = 0
    buffer_full = False

    @cached_property
    def _get_t0(self):
        return self.offset/self.fs

    @cached_property
    def _get_samples(self):
        return int(self.window * self.fs)

    def _buffer_default(self):
        return np.empty(self.samples)

    def _samples_changed(self):
        self.buffer = np.empty(self.samples)
        self.offset = 0
        self.dropped = 0
        self.partial_idx = 0
        self._write = self._partial_write

    def _get_signal(self):
        return self.buffer

    def _partial_write(self, data):
        size = data.shape[-1]
        if size > self.samples:
            # If we have too much data to write to the buffer, drop the extra
            # samples.  Offset should be incremented by the number of samples
            # dropped.  Furthermore, we now have a "full" buffer so we switch to
            # the _full_write method from now on.
            self.buffer = data[..., -self.samples:]
            self.dropped = size-self.samples
            self.offset = size-self.samples
            # Switch to the full write mode
            del self.partial_idx
            self.buffer_full = True
            self._write = self._full_write
        elif self.partial_idx+size > self.samples:
            # If the number of samples available is greater than the remaining
            # slots in the buffer, write what we can to the buffer and then
            # switch to _full_write for the remaining samples.
            overflow_size = (self.partial_idx+size)-self.samples
            initial_size = size-overflow_size
            self.buffer[..., self.partial_idx:] = data[..., :initial_size]
            # Switch to the full write mode
            del self.partial_idx
            self.buffer_full = True
            self._write = self._full_write
            # Write the remaining samples to the buffer
            self._write(data[..., -overflow_size:])
        else:
            self.buffer[..., self.partial_idx:self.partial_idx+size] = data
            self.partial_idx += size

    def _full_write(self, data):
        size = data.shape[-1]
        if size == 0:
            return
        elif size > self.samples:
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

    def get_size(self):
        if self.buffer_full:
            return self.samples
        else:
            return self.partial_idx

class MultiChannel(Channel):

    channels = Int(8)

    def _get_signal(self):
        return self.buffer

    def _write(self, data):
        self.buffer.append(data)

class RAMMultiChannel(RAMChannel, MultiChannel):

    def _buffer_default(self):
        return np.empty((self.channels, self.samples))

    def _samples_changed(self):
        self.buffer = np.empty((self.channels, self.samples))
        self.offset = 0
        self.dropped = 0
        self.partial_idx = 0
        self._write = self._partial_write

class FileMultiChannel(MultiChannel, FileChannel):

    channels = Int(8)
    name = 'FileMultiChannel'

    def _get_shape(self):
        return (self.channels, 0)

    def _buffer_default(self):
        buffer = super(FileMultiChannel, self)._buffer_default()
        buffer.setAttr('channels', self.channels)
        return buffer

#class SnippetChannel(Channel):
#
#    buffer = Instance(SoftwareRingBuffer)
#    samples = Int
#    history = Int
#    signal = Property(Array(dtype='f'))
#    average_signal = Property(Array(dtype='f'))
#    buffered = Int(0)
#    buffer_full = Bool(False)
#
#    @on_trait_change('samples, fs, history')
#    def _configure_buffer(self):
#        self.buffer = SoftwareRingBuffer((self.history, self.samples))
#
#    def _get_t(self):
#        return np.arange(-self.samples, 0) / self.fs
#
#    def _get_signal(self):
#        return self.buffer.buffered
#
#    def send(self, data):
#        # Ensure that 1D arrays containing a single snippet are broadcast
#        # properly to the correct shape.
#        data.shape = (-1, self.samples)
#        added = self.buffer.write(data)
#
#        if self.buffer_full:
#            self.updated = added, added
#        else:
#            self.buffered += added
#            if self.buffered > self.history:
#                self.buffer_full = True
#                removed = self.buffered % self.history
#                self.buffer_full
#                self.updated = removed, added
#            else:
#                self.updated = 0, added
#
#    def _get_average_signal(self):
#        return self.buffer.buffered.mean(0)
#
#    def __len__(self):
#        return self.samples

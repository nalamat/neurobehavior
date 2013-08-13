
import pyMCStream as mc

'''
:mod:`cns.channel` -- Container for timeseries data
===================================================

.. module:: cns.channel
    :platform: Unix, Windows, OSX
    :synopsis: Provides containers for timeseries data
.. moduleauthor:: 
    Brad Buran <bburan@alum.mit.edu>

The majority of these containers are backed by a HDF5 datastore (e.g. an EArray)
for acquiring and caching data.  If you just want a temporary dataset, create a
temporary array.  However, if you wish to have an in-memory datastore, you can
define a MemoryMixin class (see :class:`FileMixin`) that implements a
__getitem__ method.
'''

from traits.api import HasTraits, Property, Array, Int, Event, \
    Instance, on_trait_change, Bool, Any, String, Float, cached_property, \
    Enum, Set
import numpy as np
import tables
from scipy import signal
from .arraytools import slice_overlap
from . import h5 

import logging
log = logging.getLogger(__name__)

class FileMixin(HasTraits):
    '''
    Mixin class that uses a HDF5_ EArray as the backend for the buffer.  If the
    array does not exist, it will be created automatically.  Note that this does
    have some performance implications since data may have to be transferred
    between the hard disk and RAM.

    By default, this will create the node.  If the node already exists, use the
    `from_node` classmethod to return an instance of the class.

    IMPORTANT! When using this mixin with most subclasses of Channel, the
    FileMixin typically must appear first in the list otherwise you may have
    some method resolution order issues.

    .. _HDF5: http://www.hdfgroup.org/HDF5/

    Properties
    ----------
    dtype
        Default is float64.  It is a good idea to set dtype appropriately for
        the waveform (e.g. use a boolean dtype for TTL data) to minimize file
        size.
    node
        A HDF5 node that will host the array
    name
        Name of the array
    expected_duration
        Rough estimate of how long the waveform will be.  This is used (in
        conjunction with fs) to optimize the "chunksize" when creating the
        array.

    Compression properties
    ----------------------
    compression_level
        Between 0 and 9, with 0=uncompressed and 9=maximum
    compression_type
        zlib, lzo or bzip
    use_checksum
        Ensures data integrity, but at cost of degraded read/write performance

    Default settings for the compression filter are no compression which
    provides the best read/write performance. 
    
    Note that if compression_level is > 0 and compression_type is None,
    tables.Filter will raise an exception.
    '''

    # According to http://www.pytables.org/docs/manual-1.4/ch05.html the best
    # compression method is LZO with a compression level of 1 and shuffling, but
    # it really depends on the type of data we are collecting.
    compression_level   = Int(0, transient=True)
    compression_type    = Enum(None, 'lzo', 'zlib', 'bzip', 'blosc',
                               transient=True)
    use_checksum        = Bool(False, transient=True)
    use_shuffle         = Bool(False, transient=True)
    
    # It is important to implement dtype appropriately, otherwise it defaults to
    # float64 (double-precision float).
    dtype               = Any(transient=True)

    # Duration is in seconds.  The default corresponds to a 30 minute
    # experiment, which we seem to have settled on as the "standard" for running
    # appetitive experiments.
    expected_duration   = Float(1800, transient=True) 
    signal              = Property
    
    # The actual source where the data is stored.  Node is the HDF5 Group that
    # the EArray is stored under while name is the name of the EArray.
    node                = Instance(tables.group.Group, transient=True)
    name                = String('FileChannel', transient=True)
    _buffer             = Instance(tables.array.Array, transient=True)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.node._v_file.close()
        return False
    
    @classmethod
    def from_file(cls, filename, node_path, **kwargs):
        fh = tables.open_file(filename)
        node = h5.rgetattr(fh.root, node_path)
        return cls.from_node(node, **kwargs)

    @classmethod
    def from_node(cls, node, **kwargs):
        '''
        Create an instance of the class from an existing node
        '''
        # If the attribute (e.g. fs or t0) are not provided, load the value of
        # the attribute from the node attributes
        for name in cls.class_trait_names(attr=True):
            if name not in kwargs:
                try:
                    kwargs[name] = node._v_attrs[name]
                except KeyError:
                    # This checks for an older verison of the physiology channel
                    # data format that did not save t0 as an attribute to the
                    # node.
                    if name == 't0':
                        kwargs['t0'] = 0
                    else:
                        raise

        kwargs['node'] = node._v_parent
        kwargs['name'] = node._v_name
        kwargs['_buffer'] = node
        kwargs['dtype'] = node.dtype
        instance = cls(**kwargs)
        instance.changed = True
        return instance

    def _get_shape(self):
        return (0,)

    def __buffer_default(self):
        log.debug('%s: creating buffer with shape %r', self, self._get_shape())
        atom = tables.Atom.from_dtype(np.dtype(self.dtype))
        log.debug('%s: creating buffer with type %r', self, self.dtype)
        filters = tables.Filters(complevel=self.compression_level,
                complib=self.compression_type, fletcher32=self.use_checksum,
                shuffle=self.use_shuffle)
        earray = self.node._v_file.create_earray(self.node._v_pathname,
                self.name, atom, self._get_shape(), filters=filters,
                expectedrows=int(self.fs*self.expected_duration))
        for k, v in self.trait_get(attr=True).items():
            earray._v_attrs[k] = v
        return earray

    # Ensure that all 'Traits' are synced with the file so we have that
    # information stored away.
    @on_trait_change('+attr', post_init=True)
    def update_attrs(self, name, new):
        log.debug('%s: updating %s to %r', self, name, new)
        self._buffer.set_attr(name, new)

    def _write(self, data):
        self._buffer.append(data)

    def append(self, data):
        self._buffer.append(data)

    def __repr__(self):
        return '<HDF5 node {}>'.format(self.name)

class MCStreamMixin(HasTraits):
    '''
    Mixin class that uses a HDF5_ EArray as the backend for the buffer.  If the
    array does not exist, it will be created automatically.  Note that this does
    have some performance implications since data may have to be transferred
    between the hard disk and RAM.

    By default, this will create the node.  If the node already exists, use the
    `from_node` classmethod to return an instance of the class.

    IMPORTANT! When using this mixin with most subclasses of Channel, the
    FileMixin typically must appear first in the list otherwise you may have
    some method resolution order issues.

    .. _HDF5: http://www.hdfgroup.org/HDF5/

    Properties
    ==========
    dtype
        Default is float64.  It is a good idea to set dtype appropriately for
        the waveform (e.g. use a boolean dtype for TTL data) to minimize file
        size.
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

    Default settings for the compression filter are no compression which
    provides the best read/write performance. 
    
    Note that if compression_level is > 0 and compression_type is None,
    tables.Filter will raise an exception.
    '''

    # It is important to implement dtype appropriately, otherwise it defaults to
    # float64 (double-precision float).
    dtype               = Any(transient=True)

    signal              = Property
    
    # The actual source where the data is stored.  Node is the HDF5 Group that
    # the EArray is stored under while name is the name of the EArray.
    name                = String('anlg0001', transient=True)
    _buffer             = Any

    @classmethod
    def from_file(cls, filename, stream_name, **kw):
        stream = mc.open_stream(filename, stream_name)
        return cls.from_stream(stream, **kw)

    @classmethod
    def from_stream(cls, stream, **kw):
        for name in cls.class_trait_names(attr=True):
            if name not in kw:
                try:
                    kw[name] = getattr(stream, name)
                except AttributeError:
                    pass
        kw['_buffer'] = stream
        return cls(stream=stream, **kw)

    def _get_shape(self):
        if self._buffer is not None:
            return self._buffer.shape
        else:
            return (0,)

    def __repr__(self):
        return '<MCStream {}>'.format(self.name)

class Timeseries(HasTraits):

    updated = Event
    added   = Event
    fs      = Float(attr=True)
    t0      = Float(0, attr=True)

    def send(self, timestamps):
        if len(timestamps):
            self.append(timestamps)
            self.added = np.array(timestamps)/self.fs

    def get_range(self, lb, ub):
        ts = self._buffer.read()
        ilb = int(lb*self.fs)
        iub = int(ub*self.fs)
        mask = (ts>=ilb) & (ts<iub)
        return ts[mask]/self.fs

    def latest(self):
        if len(self._buffer) > 0:
            return self._buffer[-1]/self.fs
        else:
            np.nan

    def __getitem__(self, slice):
        return self._buffer[slice]/self.fs

    def __len__(self):
        return len(self._buffer)

class FileTimeseries(FileMixin, Timeseries):
    '''
    Timeseries class using a HDF5 node as the datastore
    '''

    name  = 'FileTimeseries'
    dtype = Any(np.int32)

class Epoch(HasTraits):

    added = Event
    fs = Float(attr=True)
    t0 = Float(0, attr=True)

    def get_range(self, lb, ub):
        timestamps = self._buffer[:]
        starts = timestamps[:,0]
        ends = timestamps[:,1]
        ilb = int(lb*self.fs)
        iub = int(ub*self.fs)
        start_mask = (starts >= ilb) & (starts < iub)
        end_mask = (ends >= ilb) & (ends < iub)
        mask = start_mask | end_mask
        if mask.any():
            return timestamps[mask,:]/self.fs
        else:
            return np.array([]).reshape((0,2))

    def send(self, timestamps):
        if len(timestamps):
            self.append(timestamps)
            self.added = np.array(timestamps)/self.fs

    def __getitem__(self, key):
        return self._buffer[key]/self.fs

class FileEpoch(FileMixin, Epoch):
    '''
    Epoch class using a HDF5 node as the datastore
    '''

    name  = 'FileEpoch'
    dtype = Any(np.int32)
    
    def _get_shape(self):
        if self._buffer is not None:
            return self._buffer.shape
        else:
            return (0, 2)

class Channel(HasTraits):
    '''
    Base class for dealing with a continuous stream of data sampled at a fixed
    rate, fs (cycles per time unit), starting at time t0 (time unit).  This
    class is not meant to be used directly since it does not implement a backend
    for storing the data.  Subclasses are responsible for implementing the data
    buffer (e.g. either a file-based or memory-based buffer).

    fs
        Sampling frequency
    t0
        Time offset (i.e. time of first sample) relative to the start of
        acquisition.  This typically defaults to zero; however, some subclasses
        may discard old data (e.g.  :class:`RAMChannel`), so we need to factor
        in the time offset when attempting to extract a given segment of the
        waveform for analysis.  

    Two events are supported.

    added
        New data has been added. If listeners have been caching the results of
        prior computations, they can assume that older data in the cache is
        valid. 
    changed
        The underlying dataset has changed, but the time-range has not.

    The changed event roughly corresponds to changes in the Y-axis (i.e. the
    signal) while added roughly corresponds to changes in the X-axis (i.e.
    addition of additional samples).
    '''

    # Sampling frequency of the data stored in the buffer
    fs = Float(attr=True, transient=True)

    # Time of first sample in the buffer.  Typically this is 0, but if we delay
    # acquisition or discard "old" data (e.g. via a RAMBuffer), then we need to
    # update t0.
    t0          = Float(0, attr=True, transient=True)

    #_buffer     = Any
    added       = Event
    changed     = Event
    #shape       = Property(depends_on=['samples'], transient=True)
    #duration    = Property(depends_on=['samples', 'fs'], transient=True)
    #samples     = Property(depends_on=['changed', 'added'], transient=True)

    def _get_samples(self):
        return self._buffer.shape[-1]

    def _get_duration(self):
        return self.samples/self.fs

    def _get_shape(self):
        return self._buffer.shape

    def __getitem__(self, slice):
        '''
        Delegates to the __getitem__ method on the underlying buffer

        Subclasses can add additional data preprocessing by overriding this
        method.  See `ProcessedFileMultiChannel` for an example.
        '''
        return self._buffer[slice]

    def to_index(self, time):
        '''
        Convert time to the corresponding index in the waveform.  Note that the
        index may be negative if the time is less than t0.  Since Numpy allows
        negative indices, be sure to check the value.
        '''
        return int((time-self.t0)*self.fs)

    def to_indices(self, time):
        '''
        Convert time array to the corresponding indices in the waveform.  Note
        that the index may be negative if the time is less than t0.  Since Numpy
        allows negative indices, be sure to check the value.
        '''
        time = np.asanyarray(time)
        return ((time-self.t0)*self.fs).astype('i')

    def to_samples(self, time):
        '''
        Convert time to number of samples.  If you want time as an index into
        the underlying channel data (e.g. corrected for t0), see
        `Channel.to_index` and `Channel.to_indices`.
        '''
        samples = np.asanyarray(time)*self.fs
        return samples.astype('i')

    def get_range_index(self, start, end, reference=0, check_bounds=False):
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
        check_bounds : bool
            Check that start and end fall within the valid data range
        '''
        t0_index = int(self.t0*self.fs)
        lb = start-t0_index+reference
        ub = end-t0_index+reference

        if check_bounds:
            if lb < 0:
                raise ValueError, "start must be >= 0"
            if ub >= len(self._buffer):
                raise ValueError, "end must be <= signal length"

        if np.iterable(lb):
            return [self[..., lb:ub] for lb, ub in zip(lb, ub)]
        else:
            return self[..., lb:ub]

    def get_index(self, index, reference=0):
        t0_index = int(self.t0*self.fs)
        index = max(0, index-t0_index+reference)
        return self[..., index]

    def _to_bounds(self, start, end, reference=None):
        if start > end:
            raise ValueError("Start time must be < end time")
        if reference is not None:
            ref_idx = self.to_index(reference)
        else:
            ref_idx = 0
        lb = max(0, self.to_index(start)+ref_idx)
        ub = max(0, self.to_index(end)+ref_idx)
        return lb, ub

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
        lb, ub = self._to_bounds(start, end, reference)
        log.debug('%s: %d:%d requested', self, lb, ub)
        return self[..., lb:ub]

    def get_size(self):
        return self._buffer.shape[-1]

    def get_bounds(self):
        '''
        Returns valid range of times as a tuple (lb, ub)
        '''
        return self.t0, self.t0 + self.get_size()/self.fs

    def latest(self):
        if self.get_size() > 0:
            return self._buffer[-1]/self.fs
        else:
            return self.t0

    def send(self, data):
        '''
        Convenience method that allows us to use a Channel as a "sink" for a
        processing pipeline.
        '''
        if len(data):
            self.write(data.ravel())

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
        self.added = lb/self.fs, ub/self.fs

    def summarize(self, timestamps, offset, duration, fun):
        if len(timestamps) == 0:
            return np.array([])

        # Channel.to_samples(time) converts time (in seconds) to the
        # corresponding number of samples given the sampling frequency of the
        # channel.  If the trial begins at sample n, then we want to analyze
        # contact during the interval [n+lb_index, n+ub_index).
        lb_index = self.to_samples(offset)
        ub_index = self.to_samples(offset+duration)
        timestamps = self.to_samples(timestamps)

        # Variable ts is the sample number at which the trial began and is a
        # multiple of the contact sampling frequency.
        # Channel.get_range_index(lb_sample, ub_sample, reference_sample) will
        # return the specified range relative to the reference sample.  Since we
        # are interested in extracting the range [contact_offset,
        # contact_offset+contact_dur) relative to the timestamp, we need to
        # first convert the range to the number of samples (which we did above
        # where we have it as [lb_index, ub_index)).  Since our reference index
        # (the timestamp) is already in the correct units, we don't need to
        # convert it.
        if np.iterable(timestamps):
            range = self.get_range_index(lb_index, ub_index, timestamps)
            return np.array([fun(r) for r in range])
        else:
            range = self.get_range_index(lb_index, ub_index, timestamps)
            return fun(range)

    @property
    def n_samples(self):
        return self._buffer.shape[-1]

    def get_segments(self, start, duration):
        '''
        Load snippets of the continuous waveform

        Parameters
        ----------
        start : iterable of float
            Start time of each segment (in seconds)
        duration : float
            Duration of each segment (in seconds)

        Returns
        -------
        Array of segment x channel x time
        '''
        segments = []
        for ts in start:
            s = self.get_range(ts, ts+duration)
            segments.append(s[np.newaxis])
        return np.concatenate(segments)

class FileChannel(FileMixin, Channel):
    '''
    Uses a HDF5 datastore for the buffer
    '''

    name  = 'FileChannel'
    dtype = Any(np.float32)

class RAMChannel(Channel):
    '''
    Buffers data in memory without saving it to disk.

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

    # Default to 0 to make it clear that the class has not been properly
    # initialized
    channels = Int(0, attr=True)

    def get_channel_range(self, channel, lb, ub):
        return self.get_range(lb, ub)[channel]

    def send(self, data):
        if len(data):
            self.write(data)

    def get_range(self, start, end, reference=None, channels=None):
        lb, ub = self._to_bounds(start, end, reference)
        if channels is None:
            channels = Ellipsis
        return self[..., lb:ub][channels]

    def get_segment(self, start_time, duration, channels=Ellipsis):
        lb, ub = self._to_bounds(start_time, start_time+duration)
        return self[channels, lb:ub]

    def segments(self, start_times, duration, channels=None):
        '''
        Returns iterator to loop through the segments
        '''
        for t in start_times:
            yield self.get_segment(t, duration, channels=channels)

    def get_segments(self, start_times, duration, channels=None):
        samples = self.to_index(duration)
        segments = []
        for i in self.to_indices(start_times):
            s = self.get_range_index(i, i+samples, channels=channels)
            segments.append(s[np.newaxis])
        return np.concatenate(segments)

    def get_range_index(self, start, end, reference=0, check_bounds=False,
                        channels=None):
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
        check_bounds : bool
            Check that start and end fall within the valid data range
        '''
        t0_index = int(self.t0*self.fs)
        lb = start-t0_index+reference
        ub = end-t0_index+reference

        if check_bounds:
            if lb < 0:
                raise ValueError, "start must be >= 0"
            if ub >= len(self._buffer):
                raise ValueError, "end must be <= signal length"

        if channels is None:
            channels = Ellipsis

        if np.iterable(lb):
            return [self[channels, lb:ub] for lb, ub in zip(lb, ub)]
        else:
            return self[channels, lb:ub]


    def summarize(self, timestamps, offset, duration, fun, channels=None):
        if len(timestamps) == 0:
            return np.array([])

        # Channel.to_samples(time) converts time (in seconds) to the
        # corresponding number of samples given the sampling frequency of the
        # channel.  If the trial begins at sample n, then we want to analyze
        # contact during the interval [n+lb_index, n+ub_index).
        lb_index = self.to_samples(offset)
        ub_index = self.to_samples(offset+duration)
        timestamps = self.to_samples(timestamps)

        # Variable ts is the sample number at which the trial began and is a
        # multiple of the contact sampling frequency.
        # Channel.get_range_index(lb_sample, ub_sample, reference_sample) will
        # return the specified range relative to the reference sample.  Since we
        # are interested in extracting the range [contact_offset,
        # contact_offset+contact_dur) relative to the timestamp, we need to
        # first convert the range to the number of samples (which we did above
        # where we have it as [lb_index, ub_index)).  Since our reference index
        # (the timestamp) is already in the correct units, we don't need to
        # convert it.
        if np.iterable(timestamps):
            range = self.get_range_index(lb_index, ub_index, timestamps,
                                         channels=channels)
            return np.array([fun(r) for r in range])
        else:
            range = self.get_range_index(lb_index, ub_index, timestamps,
                                         channels=channels)
            return fun(range)


class ProcessedMultiChannel(MultiChannel):
    '''
    References and filters the data when requested
    '''

    # Channels in the list should use zero-based indexing (e.g. the first
    # channel is 0).
    bad_channels        = Array(dtype='int')
    diff_mode           = Enum('all good', None)
    diff_matrix         = Property(depends_on='bad_channels, diff_mode, channels')

    filter_freq_lp      = Float(6e3, filter=True)
    filter_freq_hp      = Float(300, filter=True)
    filter_btype        = Enum('highpass', 'bandpass', 'lowpass', None,
                               filter=True)
    filter_order        = Float(8.0, filter=True)
    filter_type         = Enum('butter', 'ellip', 'cheby1', 'cheby2', 'bessel',
                               filter=True)

    filter_instable     = Property(depends_on='filter_coefficients')
    filter_coefficients = Property(depends_on='+filter, fs')

    _padding            = Property(Int, depends_on='filter_order')

    @cached_property
    def _get_filter_instable(self):
        b, a = self.filter_coefficients
        return not np.all(np.abs(np.roots(a)) < 1)

    @on_trait_change('filter_coefficients, diff_matrix')
    def _fire_change(self):
        # Objects that use this channel as a datasource need to know when the
        # data changes.  Since changes to the filter coefficients, differential
        # matrix or filter function affect the entire dataset, we fire the
        # changed event.  This will tell, for example, the
        # ExtremesMultiChannelPlot to clear it's cache and redraw the entire
        # waveform.
        self.changed = True

    @cached_property
    def _get_diff_matrix(self):
        if self.diff_mode is None:
            return np.identity(self.channels)
        else:
            matrix = np.identity(self.channels)

            # If all but one channel is bad, this will raise a
            # ZeroDivisionError.  I'm going to let this error "bubble up" since
            # the user should realize that they are no longer referencing their
            # data in that situation.
            weight = 1.0/(self.channels-1-len(self.bad_channels))

            for r in range(self.channels):
                if r in self.bad_channels:
                    matrix[r, r] = 0
                else:
                    for i in range(self.channels):
                        if (not i in self.bad_channels) and (i != r):
                            matrix[r, i] = -weight
            return matrix

    @cached_property
    def _get_filter_coefficients(self):
        if self.filter_btype is None:
            return [], []
        if self.filter_btype == 'bandpass':
            Wp = np.array([self.filter_freq_hp, self.filter_freq_lp])
        elif self.filter_btype == 'highpass':
            Wp = self.filter_freq_hp
        else:
            Wp = self.filter_freq_lp
        Wp = Wp/(0.5*self.fs)

        return signal.iirfilter(self.filter_order, Wp, 60, 2,
                                ftype=self.filter_type,
                                btype=self.filter_btype, 
                                output='ba')

    @cached_property
    def _get__padding(self):
        return int(3*self.filter_order)

    def __getitem__(self, slice):
        # We need to stabilize the edges of the chunk with extra data from
        # adjacent chunks.  Expand the time slice to obtain this extra data.
        padding = self._padding
        data = slice_overlap(self._buffer, slice[-1], padding, padding)

        # It does not matter whether we compute the differential first or apply
        # the filter.  Since the differential requires data from all channels
        # while filtering does not, we compute the differential first then throw
        # away the channels we do not need.
        data = self.diff_matrix.dot(data)

        # For the filtering, we do not need all the channels, so we can throw
        # out the extra channels by slicing along the second axis
        data = data[slice[:-1]]
        if self.filter_btype is not None:
            b, a = self.filter_coefficients
            # Since we have already padded the data at both ends padlen can be
            # set to 0.  The "unstable" edges of the filtered waveform will be
            # chopped off before returning the result.
            data = signal.filtfilt(b, a, data, padlen=0)
        return data[..., padding:-padding]

class ProcessedFileMultiChannel(FileMixin, ProcessedMultiChannel):
    pass

class RAMMultiChannel(RAMChannel, MultiChannel):

    def _buffer_default(self):
        return np.empty((self.channels, self.samples))

    def _samples_changed(self):
        self.buffer = np.empty((self.channels, self.samples))
        self.offset = 0
        self.dropped = 0
        self.partial_idx = 0
        self._write = self._partial_write

class FileMultiChannel(FileMixin, MultiChannel):

    name = 'FileMultiChannel'

    def _get_shape(self):
        if self._buffer is not None:
            return self._buffer.shape
        else:
            return (self.channels, 0)

    def __repr__(self):
        t = '<HDF5 node {}, {} channels, {} Hz>'
        return t.format(self.name, self.channels, self.fs)

class FileSnippetChannel(FileChannel):

    snippet_size        = Int
    classifiers         = Any
    timestamps          = Any
    unique_classifiers  = Set

    def __getitem__(self, key):
        return self._buffer[key]

    def _classifiers_default(self):
        atom = tables.Atom.from_dtype(np.dtype('int32'))
        earray = self.node._v_file.create_earray(self.node._v_pathname,
                self.name + '_classifier', atom, (0,),
                expectedrows=int(self.fs*self.expected_duration))
        return earray

    def _timestamps_default(self):
        atom = tables.Atom.from_dtype(np.dtype('int32'))
        earray = self.node._v_file.create_earray(self.node._v_pathname,
                self.name + '_ts', atom, (0,),
                expectedrows=int(self.fs*self.expected_duration))
        return earray
    
    def _get_shape(self):
        return (0, self.snippet_size)

    def send(self, data, timestamps, classifiers):
        if len(data):
            data.shape = (-1, self.snippet_size)
            self._buffer.append(data)
            self.classifiers.append(classifiers)
            self.timestamps.append(timestamps)
            self.unique_classifiers.update(set(classifiers))
            self.added = data, timestamps, classifiers

    def get_recent(self, history=1, classifier=None):
        if len(self._buffer) == 0:
            return np.array([]).reshape((-1, self.snippet_size))
        spikes = self._buffer[-history:]
        if classifier is not None:
            classifiers = self.classifiers[-history:]
            mask = classifiers[:] == classifier
            return spikes[mask]
        return spikes

    def get_recent_average(self, count=1, classifier=None):
        return self.get_recent(count, classifier).mean(0)

class MCMultiChannel(MCStreamMixin, MultiChannel):
    pass

class MCProcessedMultiChannel(MCStreamMixin, ProcessedMultiChannel):
    pass

def open_mcfile(*args, **kwargs):
    return FileMultiChannel.from_file(*args, **kwargs)
    
if __name__ == '__main__':
    import doctest
    doctest.testmod()

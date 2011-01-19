import numpy as np
from math import floor
import logging

log = logging.getLogger(__name__)

#def wrap(offset, length, buffer_size):
#    """Utility method designed to handle buffer boundary conditions for
#    functions using a ring-style buffer by checking to see if the combined
#    length and offset result in an operation beyond the end of the buffer.  If
#    so, indices are split accordingly so it wraps around properly.
#
#    Returns a tuple of tuples containing the sectors that need to be joined.
#    """
#    if (offset+length)>buffer_size:
#        a_length = buffer_size-offset
#        b_length = length-a_length
#        return ((offset, a_length), (0, b_length))
#    else:
#        return ((offset, length), )

#def available(old_idx, new_idx, buffer_size, multiple=1):
#    '''Returns the number of samples for the next read given the buffer size
#    (which allows it to accurately estimate the read size for ring buffers where
#    the index has wrapped around to the beginning).
#
#        old_idx         Index that last read terminated on
#        new_idx         Current index of the buffer
#        buffer_size     Size of the buffer
#        multiple        Requires that read size be a multiple of this value.
#                        This is important for buffers that acquire "blocks" or
#                        "snippets" of fixed size (such as the spike waveforms)
#                        since it is possible to attempt a read while the buffer
#                        is currently acquiring a new snippet.  This results in
#                        the read acquiring an incomplete snippet.
#    '''
#    if new_idx<old_idx:
#        available = buffer_size-old_idx+new_idx
#    else:
#        available = new_idx-old_idx
#    return floor(available/multiple)*multiple

class Buffer(object):

    pass

    #def __init__(self, length):
    #    self.length = length

    #def __len__(self):
    #    return self.length
    #
#class NewSoftwareRingBuffer(Buffer):
#    """This buffer will drop samples if too much data is streamed to it.  This
#    is mainly intended for plotting."""
#
#    samples = 0
#    dropped = 0
#
#    def __init__(self, size):
#        '''Size parameter can be a tuple allowing for buffers with multiple
#        dimensions (i.e. for storing multiple channels of data.  The first
#        dimension is considered the length of the buffer.
#        '''
#        self._data = np.zeros(size)
#        Buffer.__init__(self, len(self._data))
#
#    def write(self, data):
#        while data.ndim < self._data.ndim:
#            new_shape = [1]
#            new_shape.extend(data.shape)
#            data.shape = new_shape
#
#        size = len(data)
#        if size:
#            #self.samples += size
#            if len(data) > len(self._data):
#                self._data[:] = data[-len(self._data):]
#                #self.dropped += size-len(self)
#                #return len(self)
#            elif len(data) < len(self._data):
#                self._data[self.offset:]
#                remainder = len(self)-size
#                if remainder:
#                    self._data[:remainder] = self._data[-remainder:]
#                #self._data[-size:] = data
#                self._data[:size] = data
#                return size
#
#    def _read(self, offset, length):
#        return self._data[offset:offset+length]
#
#    def _get_data(self):
#        return self._data
#
#    def _get_buffered_data(self):
#        if self.samples:
#            return self.data[-self.samples:]
#        else:
#            shape = list(self.data.shape)
#            shape[0] = -1
#            return np.array([]).reshape(shape)
#
#    def _get_buffer_full(self):
#        return self.samples >= len(self)
#
#    data = property(_get_data)
#    buffered = property(_get_buffered_data)
#    buffer_full = property(_get_buffer_full)

class SoftwareRingBuffer(Buffer):
    """This buffer will drop samples if too much data is streamed to it.  This
    is mainly intended for plotting."""

    samples = 0
    dropped = 0

    def __init__(self, size):
        '''Size parameter can be a tuple allowing for buffers with multiple
        dimensions (i.e. for storing multiple channels of data.  The first
        dimension is considered the length of the buffer.
        '''
        self._data = np.zeros(size)
        Buffer.__init__(self, len(self._data))

    def write(self, data):
        while data.ndim < self._data.ndim:
            new_shape = [1]
            new_shape.extend(data.shape)
            data.shape = new_shape

        size = len(data)
        if size:
            self.samples += size
            if size > len(self):
                self._data = data[-len(self):]
                self.dropped += size-len(self)
                return len(self)
            else:
                remainder = len(self)-size
                if remainder:
                    self._data[:remainder] = self._data[-remainder:]
                self._data[-size:] = data
                return size

    def _read(self, offset, length):
        return self._data[offset:offset+length]

    def _get_data(self):
        return self._data

    def _get_buffered_data(self):
        if self.samples:
            return self.data[-self.samples:]
        else:
            shape = list(self.data.shape)
            shape[0] = -1
            return np.array([]).reshape(shape)

    def _get_buffer_full(self):
        return self.samples >= len(self)

    data = property(_get_data)
    buffered = property(_get_buffered_data)
    buffer_full = property(_get_buffer_full)

class RingBuffer(Buffer):

    # Index tracks current position of buffer
    index  = 0

    # Cycle tracks number of times buffer has wrapped around to the beginning.
    # Start at -1 (i.e. means that the buffer has not started acquiring data
    # yet).  The very first call to read will set cycle to 0.
    cycle = -1

    def _wrap(self, length):
        offset = self.index
        buffer_size = self.size

        if (offset+length) > buffer_size:
            a_length = buffer_size-offset
            b_length = length-a_length
            return ((offset, a_length), (0, b_length))
        else:
            return ((offset, length), )

    def pending(self):
        raise NotImplementedError

    def read(self, size=None):
        if size is None:
            size = self.pending()
        data = [self._read(o, l) for o, l in self._wrap(size)]

        # Store the last index read in self.index
        self.index = o+l

        # If offset is 0, that means we've wrapped around to the beginning.
        # Note that the very first call to read will have an offset of 0, so
        # this will increment the cycle.
        if o == 0:
            self.cycle += 1
        return np.concatenate(data, axis=1)

    def write(self, data):
        size = len(data)
        log.debug("Writing %d samples to %s", size, self)
        if size == 0:
            return
        if size > self.size:
            mesg = 'An attempt to write %d samples to %s failed because ' + \
                   'it is greater than the size of the buffer.'
            raise ValueError, mesg % (size, self)

        num_written = 0
        for o, l in self._wrap(size):
            if not self._write(o, data[num_written:num_written+l]):
                raise SystemError, 'Problem with writing data to buffer'
            num_written += l
        self.idx = self.idx+num_written%self.length
        return num_written

    #def _get_buffered(self):
    #    if self.cycles:
    #        return self.length
    #    else:
    #        return self.idx

    #def _get_total_samples_processed(self):
    #    return self.cycles*len(self)+self.idx

    #total_samples_processed = property(_get_total_samples_processed)
    #buffered = property(_get_buffered)
    def __repr__(self):
        return '<%s[idx=%d:len=%d:cyc=%d]>' % \
                (self.__class__.__name__, self.idx, len(self), self.cycles)
    
class RAMBuffer(RingBuffer):

    samples = 0
    dropped = 0

    def __init__(self, size):
        '''Size parameter can be a tuple allowing for buffers with multiple
        dimensions (i.e. for storing multiple channels of data.  The first
        dimension is considered the length of the buffer.
        '''
        self._data = np.zeros(size)
        Buffer.__init__(self, len(self._data))

    def _write(self, offset, data):
        length = len(data)
        self._data[offset:offset+length] = data
        self.samples += length
        
    def _read(self, offset, length):
        return self._data[offset:offset+length]

#class BlockBuffer(RingBuffer):
#    """Written to facilitate updating the original behavior code (which reads
#    the buffer in half increments).  Set block size to half the buffer size as
#    needed.
#    """
#
#    def __init__(self, size, blocks=2):
#        RingBuffer.__init__(self, size)
#        self.blocks = blocks
#        #self.odd = size%blocks
#        #self.block_idx = 0
#
#    def get_block_size(self):
#        return int(len(self)/self.blocks)
#
#    block_size = property(get_block_size)
#
#    def read_block(self, blocks=1):
#        return self.read(self.block_size*blocks)
#
#    def write_block(self, data):
#        """Does not check to see if block has been processed yet before
#        writing.  To avoid overwriting an unprocessed block, use
#        blockReady().
#        """
#        if len(data) % self.block_size:
#            mesg = 'Length of data to write must be a multiple ' + \
#                   'of the block size, %d.'
#            raise ValueError, mesg % self.block_size
#        return self.write(data)

"""
Collection of classes and functions that generate an abstraction layer between
Python and TDT's drivers.  Direct calls to TDT's drivers are highly discouraged
since this means that you will have difficulty switching to a new backend in the
future (e.g. National Instrument's PXI and FGPA system).

In addition to supporting an abstraction layer, provides convenience methods and
properties for interacting with the DSP.

There are two main types of output DSP circuits: real-time and buffered.

Real-time circuit
    A real-time circuit contains the appropriate processing chain that generates
    the signal.  Signal parameters are exposed via tags.  Since the signal is
    computed on a sample-by-sample basis, changes to signal parameters are
    applied instantly.

Buffered circuit
    A buffered circuit is more generic, containing a memory buffer that stores a
    pre-generated signal that is played to the speaker on a sample-by-sample
    basis.  Since the entire signal waveform must be computed via software and
    uploaded to the DSP before it can be played, changes to signal parameters
    are not applied instantly.  The circuit can rotate through multiple buffers,
    allowing us to randomize presentations.

DSP circuits also can contain data buffers that acquire data.  These data
buffers fall into several categories

Continuous waveform
    Data is acquired continuously.  It may be decimated (i.e. a data sample is
    recorded only on every 10 DSP cycles), meaning that the actual sampling
    frequency is a fraction of the DSP clock.
Waveform segment
    In response to some external trigger, a fixed-length segment of a waveform
    is stored.  The segments are not continuous (e.g. there is a gap between
    segments).
Event times
    Circuits will have a master clock that reports time as the total number of
    cycles since the circuit was started.  This master clock is an unsigned
    32-bit integer with a maximum value of 2,147,483,647.  At a clock rate of
    200 kHz (maximum for the RX6), the clock will roll over every 2.98 hours.
    At a clock rate of 25 kHz (maximum for the RZ5), the clock will roll over
    every 23.9 hours.  Currently, rollover is unlikely to be an issue.
Post-trigger times
    Certain events can be referenced to the time of a trigger.

"""

from __future__ import division
from cns.buffer import available, BlockBuffer
from cns.util.math import nextpow2
import logging
import numpy as np
from functools import partial
log = logging.getLogger(__name__)

import os, time, re

from cns.equipment import EquipmentError
#from cns.equipment.TDT import set_attenuation

'''Mapper between Numpy datatype and TDT's ActiveX type.'''
type_lookup = {
        np.float32: 'F32',
        np.int32:   'I32',
        np.int16:   'I16',
        np.int8:    'I8',
        }

rpcox_types = {
        68:     np.ndarray,     # Data buffer
        73:     int,
        74:     'Static',       # May indicate static parameter
        78:     bool,
        83:     float,
        80:     np.ndarray,     # This is coefficient buffer?
        65:     None,           # What was this again?
        76:     'Trigger',      # Not sure how to implement this (this is a
                                # software trigger?)
        }

VALID_UNITS = 'fs', 'Hz', 's', 'ms', 'nPow2', 'n', 'nPer'
P_UNIT = re.compile(r".*_(%s)$" % '|'.join(VALID_UNITS))

def convert(src_unit, dest_unit, value, dsp_fs):
    '''
    Converts value to desired unit give the sampling frequency of the DSP.

    Parameters specified in paradigms are typically expressed as
    frequency and time while many DSP parameters are expressed in number of
    samples (referenced to the DSP sampling frequency).  This function provides
    a convenience method for converting between conventional values and the
    'digital' values used by the DSP.

    Note that for converting units of time/frequency to n/nPer, we have to
    coerce the value to a multiple of the DSP period (e.g. the number of 'ticks'
    of the DSP clock).

    Appropriate strings for the unit types:
        fs
            sampling frequency
        nPer
            number of samples per period
        n
            number of samples
        s
            seconds
        ms
            milliseconds
        nPow2
            number of samples, coerced to the next greater power of 2 (used for
            ensuring efficient FFT computation)

    >>> convert('s', 'n', 0.5, 10000)
    5000
    >>> convert('fs', 'nPer', 500, 10000)
    20

    Parameters
    ----------
    src_unit: string
    dest_unit: string
        Destination unit
    value: numerical (e.g. integer or float)
        Value to be converted

    Returns
    -------
    numerical value
    '''

    def fs_to_nPer(req_fs, dsp_fs):
        if dsp_fs < req_fs:
            raise SamplingRateError(dsp_fs, req_fs)
        return int(dsp_fs/req_fs)

    Hz_to_nPer = fs_to_nPer
    
    def nPer_to_fs(nPer, dsp_fs):
        return dsp_fs/nPer

    nPer_to_Hz = nPer_to_fs
    
    def n_to_s(n, dsp_fs):
        return n/dsp_fs
    
    def s_to_n(s, dsp_fs):
        return int(s*dsp_fs)

    def ms_to_n(ms, dsp_fs):
        return int(ms*1e-3*dsp_fs)

    def n_to_ms(n, dsp_fs):
        return n/dsp_fs*1e3
   
    def s_to_nPow2(s, dsp_fs):
        return nextpow2(s_to_n(s, dsp_fs))

    fun = '%s_to_%s' % (src_unit, dest_unit)
    return locals()[fun](value, dsp_fs)

class CircuitError(BaseException):
    pass

class UnitError(CircuitError):
    pass

class SamplingRateError(UnitError):

    def __init__(self, fs, requested_fs):
        self.fs = fs
        self.requested_fs = requested_fs

    def __str__(self):
        mesg = 'The requested sampling rate, %f Hz, is greater than ' + \
               'the DSP clock frequency of %f Hz.'
        return mesg % (self.requested_fs, self.fs)

class DSPBuffer(BlockBuffer):
    '''
    Provides simple read/write access to the DSP buffers.  
    
    This class is meant to handle the various methods via which data can be
    stored on the DSP.  Since data can be compressed for storage in the DSP
    buffer and may contain multiple channels, you must tell the object how to
    interpret the data downloaded from the buffer by initializing it via
    :func:`DSPBuffer.initialize`.

    This class relies on strict naming conventions for the DSP tags to correctly
    download data from the DSP.

    Continuous acquire
        <buffer>_in_<type>
            name of tag connected to data port of buffer
        <buffer>_idx
            tag connected to index port of buffer
        <buffer>_n
            tag connected to size port of buffer
        <buffer>_cyc
            number of times buffer has wrapped around to the beginning

        Each time a read is requested, <buffer>_idx is checked to see if it has
        incremented since the last read.  If it has, the new data is acquired
        and returned.

    Triggered acquire 
        In addition to the tags required for continuous aquisition, we need an
        additional tag.

        <buffer>_idx_trig
            index of last sample buffer acquired prior to the trigger

        Each time a read is requested, <buffer>_idx_trig is checked to see if it
        has changed since the last read.  If it has, the new data up to
        <buffer>_idx_trig is returned.

    Buffer types
        c
            continuous waveform
        s
            segment of a waveform
        et
            event times
        ptt
            post-trigger event times

    I have been toying with the idea of creating TDT macros that handle a lot of
    the boilerplate in setting up the necessary tags for the serial buffers.  If
    I do this, then I would incorporate auto-discovery of the necessary
    parameters (e.g. sampling rate, compression settings and number of
    channels).
    '''

    def __init__(self, dsp, name):
        self.dsp = dsp
        self.name = name
        self.name_len = name + '_n'
        self.max_len = dsp.GetTagSize(name)
        self.length = dsp.GetTagVal(self.name_len)
        BlockBuffer.__init__(self, self.max_len, blocks=2)
        self.initialize()
        self._bind_activex_functions()
        
    def _bind_activex_functions(self):
        '''Freezes the Name parameter of the ActiveX function.  Do not use these
        unless absolutely necessary!
        '''
        functions = ['ReadTagV', 'ReadTagVEX', 'WriteTagV', 'WriteTagVEX']
        for f in functions:
            callable = getattr(self.dsp, f)
            setattr(self, f, partial(callable, self.name))

    def __repr__(self):
        return '<%s::%s[idx=%d:len=%d:cyc=%d]>' % \
                (self.__class__.__name__, self.name,
                 self.idx, len(self), self.cycles)
                
    def bounds(self):
        """
        Returns the minimum, maximum valid value, numerical resolution of a
        32-bit float that has been scaled and compressed to an integer for
        faster data streaming.
        """
        bits = 8*np.nbytes[self.src_type]
        return -(2**bits)/2, (2**bits)/2-1

    def resolution(self):
        return 1/self.sf
    
    def best_sf(self, max_amplitude):
        ub = self.bounds()[1]
        return np.floor(ub/max_amplitude)

    def initialize(self, src_type=np.float32, channels=1, read_mode='continuous', 
                   multiple=1, compression=None, fs=None, sf=1):
        """
        Configures class with appropriate information to interpret data acquired
        from the DSP buffer.
        """
        self.__dict__.update(locals())

        if read_mode == 'continuous':
            self.name_idx = self.name + '_idx'
        elif read_mode == 'triggered':
            self.name_idx = self.name + '_idx_trig'
        else:
            raise ValueError, '%s read not supported' % read_mode
        
        if self.compression not in [None, 'decimated', 'shuffled']:
            mesg = "{0} is not a valid compression mode".format(self.compression)
            raise ValueError, mesg
        
        #self.read_args = type_lookup[src_type], type_lookup[dest_type], 1
        #self._read_f = self.dsp.ReadTagVEX
            
        self.c_factor = int(4/np.nbytes[src_type])
        self.idx = self.dsp.GetTagVal(self.name_idx)
        read_func = self._read_mode[(self.channels==1, self.compression)]
        self._read = read_func.__get__(self, DSPBuffer)

        buf_size = self.dsp.GetTagSize(self.name)
        if buf_size % self.channels:
            mesg = 'Buffer size, %d, is not a multiple of the channel number, %d'
            mesg = mesg % (buf_size, self.channels)
            raise ValueError(mesg)
            
    def _set_length(self, length):
        #buf_size = self.dsp.GetTagVal(self.name_len)
        buf_size = self.dsp.GetTagSize(self.name)
        if length > buf_size:
            mesg = 'Cannot set size of buffer %s to %d.  Buffer size is %d.'
            raise ValueError(mesg % (self.name, length, buf_size))
        self.dsp.SetTagVal(self.name_len, length)
        self.length = length

    def set(self, data):
        '''Assumes data is written starting at the first index of the buffer.'''
        log.debug('Attempting to set buffer %s', self.name)
        try:
            data.fs = self.dsp.GetSFreq()
            self._set_length(len(data))
            self.dsp.WriteTagV(self.name, 0, data.signal)
            #PA5.SetAtten(data.level)
            #set_attenuation(data.level)
            log.debug('Set buffer %s with %d samples', self.name, len(data.signal))
        except AttributeError, e:
            self._set_length(len(data))
            self.dsp.WriteTagV(self.name, 0, data)
            log.debug('Set buffer %s with %d samples', self.name, len(data))

    def write(self, data):
        try:
            data.fs = self.fs
            super(DSPBuffer, self).write(data.signal)
        except AttributeError:
            super(DSPBuffer, self).write(data)

    def samples_processed(self):
        curidx = self.dsp.GetTagVal(self.name_idx)
        if curidx<self.idx:
            return self.length-self.idx+curidx
        else:
            return curidx-self.idx

    def block_processed(self):
        """Indicates that the next block has been processed.  If this is
        primarily an input buffer, it means the block has data that is ready for
        acquisition.  If this is primarily an output buffer, it means the data
        in the block has been processed by the system (e.g.  played to the
        speaker) and can be overwritten safely using writeBlock.
        """
        return self.samples_processed()>=self.block_size

    def available(self):
        # Very important!  We must read name_idx only once and store it locally as
        # the DSP will continue to acquire data while we are doing our processing.
        # We simply will grab the current data up to the point at which we read
        # name_idx.
        new_idx = self.dsp.GetTagVal(self.name_idx)
        return available(self.idx, new_idx, self.length, self.multiple)
    
    def _simple_read(self, offset, length):
        # Available reports the number of samples ready to be read and
        # accounts for various edge cases.  See function documentation for
        # more detail.
        if length == 0:
            return np.array([])
        else:
            #data = self._read_f(self.name, offset, length, *self.read_args)[0]
            data = self.ReadTagV(offset, length)
            # The RZ5 and RX6 use float32 as the native datatype.  Numpy appears
            # to use float64 by default.
            return np.array(data, dtype=np.float32)
        
    def _c_read(self, offset, length):
        '''
        We could use the TDT ReadTagVEX function and pass the appropriate data
        type parameters (e.g. I8 or I16) and have it expand the 32 bit value to
        the appropriate number; however, in my tests (see test_readtag_speed.py)
        it seems pretty clear that TDT uses an inefficient algorithm for
        converting the data.  If we are converting 4 samples of data to 8 bits
        each then combining it into a 32 bit word, we would expect the read to
        be 4x faster than the uncompressed version (since we only are
        transferring 25% of the data); however, the ReadTagVEX function is only
        1.16x faster when reading compressed data.  If we just grab the raw bits
        using ReadTagV and use Numpy to convert the 32 bit values to the
        corresponding 8 bit values, it is 3.8x faster.
        '''
        data = self._simple_read(offset, length).view(self.src_type)
        return data/self.sf

    def _mc_read(self, offset, length):
        # We need to reshape the empty array to give it dimensionality
        # so that attempting to index a channel does not result in an
        # error.  For example, data[:,1] should give us [] for channel 1.
        #return np.array([]).reshape((-1, self.channels))
        return self._simple_read(offset, length).reshape((-1, self.channels))
    
    def _mc_c_read(self, offset, length):
        return self._c_read(offset, length).reshape((-1, self.channels))
    
    def _mc_dec_read(self, offset, length):
        '''
        Since two samples are compressed into a single word before being
        shuffled, the data is stored in the order A1 A2 B1 B2 C1 C2 D1 D2 A3
        A4 B3 B4 C3 C4 D3 D4 (where A through D are "channels" and 1 through 4
        are the sample number).  We need to compensate for this by using some
        fancy indexing.

        The TDT ActiveX documentation does not appear to accurately describe
        how ReadTagVEX works.  ReadTagVEX wants the number of samples
        acquired, not the buffer index.  If two samples are compressed into a
        single buffer slot, then we need to multiply the read size by 2.  If
        four samples are compressed into a single buffer slot, the read size
        needs to be 4.

        We also need to offset the read appropriately.  <Don't fully
        understand this but my test code says I've got it OK>

        Do not change the four lines below unless you test it with timeit!
        This has been optimized for speed.  See test_concatenate_time.py (in
        the same folder as this file) to see the test results.  This method is
        an order of a magnitude faster than any other method I have thought
        of.

        Use the :module:`test_readtag_speed` as needed.  The last time I ran it,
        the output was:

        LOW N
        -----
        ReadTagV(100)                     0.0290642656822
        ReadTagVEX(100)                   0.0335609266096
        ReadTagVEX(100, "I8", "F32", 1)   0.0260591935399
        ReadTagVEX(100, "I8", "F32", 4)   0.0606774144555
        ReadTagVEX(100, "F32", "F32", 4)  0.0733640589169

        HIGH N
        ------
        ReadTagV(5000)                    0.739590565484
        ReadTagVEX(5000)                  0.742036089954
        ReadTagVEX(5000, "I8", "F32", 1)  0.584825936647
        ReadTagVEX(5000, "I8", "F32", 4)  2.22288995722
        ReadTagVEX(5000, "F32", "F32", 4) 2.86715288757
        '''
        data = self._c_read(offset, length)
        temp = np.empty((len(data)/self.channels, self.channels))

        c = self.c_factor
        for i in range(self.channels):
            for j in range(c):
                temp[j::c,i] = data[i*c+j::c*self.channels]
        data = temp
        return data

    def _write(self, offset, data):
        return self.dsp.WriteTagV(self.name, offset, data)

    def _get_duration(self):
        return len(self.buffer)/self.fs

    def acquire(self, samples, trigger=None, timeout=1, dt=0.01):
        self.dsp.trigger(trigger)
        cumtime = 0
        cumsamples = 0
        data = []
        while True:
            new_data = self.read()
            cumsamples += len(new_data)
            data.append(new_data)
            if cumsamples >= samples:
                break
            elif len(new_data) > 0:
                # Reset the "clock" eachtime we get new data.  Timeout is only
                # activated when the read stalls and continually returns zero
                # samples.
                cumtime = 0
            elif timeout is not None and cumtime > timeout:
                raise IOError, 'Read from buffer %s timed out' % buffer
            time.sleep(dt)
            cumtime += dt
        return np.concatenate(data)[:samples]
    
    def channel_args(self):
        return { 'channels' : self.channels,
                 'fs'       : self.fs, }

    MC = False
    SINGLE = True
    
    _read_mode = { (SINGLE, None)        : _simple_read,
                   (SINGLE, 'decimated') : _c_read,
                   (MC, None)            : _mc_read,
                   (MC, 'shuffled')      : _mc_c_read,
                   (MC, 'decimated')     : _mc_dec_read,
                  }

class DSPTag(object):
    '''
    Wrapper around a RPvdsEx circuit tag
    
    Arguments
    ---------
    dsp : `DSPCircuit`
        Reference to circuit the tag is associated with
    name : string
        Name of tag in circuit
    type : type
        Type of tag.  When tag is accessed, it will be coerced to this type.  If
        none, no type coercion is performed.
    
    If you follow appropriate naming conventions in the DSP circuit, the get and
    set methods will be able to convert the provided value to the appropriate
    type.  For example, if the DSP tag expects number of samples (i.e. cycles of the
    DSP clock), the tag name must end in '_n'.

    >>> tag_n.set(3, src_unit='s')

    The value will then be multiplied by the DSP clock frequency and converted
    to the nearest integer before being sent to the DSP.

    To do the conversion yourself.

    >>> value = int(tag_n.dsp.fs*3)
    >>> tag_n.value = value

    Alternatively, if you do not provide a src_unit (i.e. source unit), no
    conversion is done to the value.

    >>> tag_n.set(value)

    Likewise, `DSPTag.get` supports units using the req_unit parameter (i.e.
    requested unit).  

    >>> tag_n.get(req_unit='s')
    '''

    epsilon = 1e-6

    def __init__(self, dsp, name, type):
        self.dsp = dsp
        self.fs = dsp.GetSFreq()
        self.name = name
        self.type = type
        try:
            self.unit, = P_UNIT.match(name).groups()
        except AttributeError:
            self.unit = None

    def _get_value(self):
        if type is not None:
            return self.type(self.dsp.GetTagVal(self.name))
        return self.dsp.GetTagVal(self.name)

    def _set_value(self, value):
        success = self.dsp.SetTagVal(self.name, value)
        result = self.dsp.GetTagVal(self.name)
        # Accounts for floating point inaccuracy
        if not success or not result-self.epsilon<value<result+self.epsilon:
            raise SystemError, "Hardware communication error. " + \
                    "Could not set tag %s to %r." % (self.name, value)
        else:
            log.debug('Set %s to %r', self.name, value)

    value = property(_get_value, _set_value)

    def set(self, value, src_unit=None, lb=-np.inf, ub=np.inf):
        '''
        Convert value, coerce to range [lb, ub] and upload to DPS variable
        
        Since lb and ub are set to -inf and +inf by default, no coercion is
        typically done.  This clipping is useful for some DSP components such as
        TTLDelay2.  If N1+N2=0 for TTLDelay2, the component will not relay any
        TTLs it recieves.  By ensuring that N1+N2!=1 when you want a delay of 0,
        you can avoid this issue.  Note that I typically solve this problem by
        making N1 configurable via a tag, and setting N2 to 1 that way the
        software does not need to worry about avoiding setting N1 to 0.
        '''
        if src_unit is not None:
            value = convert(src_unit, self.unit, value, self.fs)
        self.value = np.clip(value, lb, ub)

    def get(self, req_unit=None):
        if req_unit is not None:
            return convert(self.unit, req_unit, self.value, self.fs)
        else:
            return self.value

class Circuit(object):
    '''
    Acts as a loose wrapper around a RPvdsEx circuit.  The circuit exposes the
    circuit tags (i.e. variables) and buffers as class attributes.  Technically
    these attributes are instances of :class:`DSPTag` and :class:`DSPBuffer`,
    respectively.  These instances provide many convenience methods and
    attributes that facilitate coding of software for the RPvdsEx circuit.

    This class is not meant to be instantiated directly.  Typically you will use
    the factory function :func:`circuit_factory` to inspect the RPvdsEx circuit
    and attach the appropriate :class:`DSPTag` and :class:`DSPBuffer` instances
    to the Circuit instance.
    '''

    def reload(self):
        '''
        Clear DSP RAM set all variables to default value

        The circuit is reloaded from disk, so any recent edits to the circuit
        will be reflected in the running program.
        '''
        # Note that ClearCOF alone does not apear to reset all variables to
        # default value, so we reload the circuit.  This is also useful.
        self.dsp.ClearCOF()
        self.dsp.LoadCOF(self.CIRCUIT_PATH)

    def start(self, trigger=None, **kw):
        self.configure(**kw)
        if trigger is not None:
            self.trigger(trigger)
        self.dsp.Run()

    def stop(self):
        self.dsp.Halt()
        
    def configure(self, **kw):
        for k, v in kw.items():
            self.set(k, v)

    def set(self, tag, value):
        getattr(self, tag).value = value

    def get(self, tag):
        return getattr(self, tag).value

    def __str__(self):
        return self.__class__.__name__

    def _get_status(self):
        # Flip around order of bits so we can walk through them in order
        # bin is a function available only in Python 2.6+
        status = bin(self.dsp.GetStatus())[::-1]
        return status

    def _get_running(self):
        return self.status[2] == '1'

    running = property(_get_running)
    status = property(_get_status)

    def trigger(self, trig):
        log.debug('Trigger %r fired', trig)
        if trig == 'A':
            raise NotImplementedError
        elif trig == 'B':
            raise NotImplementedError
        elif type(trig) == int:
            self.dsp.SoftTrg(trig)

    def acquire(self, buffer, samples, trigger=None, timeout=1, dt=0.01):
        self.trigger(trigger)
        cumtime = 0
        cumsamples = 0

        data = []
        while True:
            new_data = buffer.read()
            cumsamples += len(new_data)
            data.append(new_data)
            if cumsamples >= samples:
                break
            elif len(new_data) > 0:
                # Reset the "clock" eachtime we get new data.  Timeout is only
                # activated when the read stalls and continually returns zero
                # samples.
                cumtime = 0
            elif timeout is not None and cumtime > timeout:
                raise IOError, 'Read from buffer %s timed out' % buffer
            
            time.sleep(dt)
            cumtime += dt
        
        return np.concatenate(data)[:samples]
    
    def convert(self, src_unit, req_unit, value):
        return convert(src_unit, req_unit, value, self.fs)

def load_cof(iface, circuit_name):
    '''Loads circuit file to DSP device.  Searches cns/equipment/TDT/components
    directory as well as working directory.'''
    # Use os.path to construct paths since this facilitates reuse of code across
    # platforms.
    search_dirs = [os.path.join(os.path.dirname(__file__), 'components'),
                   os.getcwd(), ]

    success = False
    for dir in search_dirs:
        circuit_path = os.path.join(dir, circuit_name+'.rcx')
        if os.path.exists(circuit_path):
            success = True
            break

    if not success:
        mesg = 'Could not find %s' % circuit_name
        log.critical(mesg)
        raise SystemError, mesg

    if iface.ClearCOF():
        log.debug('Cleared %s buffers' % iface)
    else:
        mesg = 'Unable to clear %s buffers' % iface
        log.critical(mesg)
        raise SystemError, mesg

    if not iface.LoadCOF(circuit_path):
        mesg = 'Unable to load %s' % circuit_path
        log.critical(mesg)
        raise SystemError, mesg

    return circuit_path

def get_tags(iface):
    '''Queries the DSP for information regarding available tags.

    Args:
        iface: iface
    '''
    num_tags = iface.GetNumOf('ParTag')
    tags = [iface.GetNameOf('ParTag', i+1) for i in range(num_tags)]
    types = [rpcox_types[iface.GetTagType(tag)] for tag in tags]
    return zip(tags, types)

def circuit_factory(circuit_name, iface):
    '''Load RPvdsEx circuit to specified DSP.  

    A subclass of :class:`DSPBuffer` is dynamically created via introspection of
    the RPvdsEx circuit.  All tags (i.e. variables) and buffers that can be read
    or written are exposed in the instance returned by this function.

    This uses a map of DSP tag/buffer types to Python types (e.g.  a DSP buffer
    should map to a :class:`DSPBuffer` instance and a TTL tag should map to a
    boolean type.  See `rpcox_types` in this module for the actual mapping.

    Parameters
    ----------
    circuit_name: string
        String identifying the circuit.  The rcx extension may be omitted if
        desired.  Since this string is passed directly to :func:`load_cof`,
        refer to that documentation for more information regarding what
        directories are searched to locate the circuit.

    iface: instance of ActiveX driver 
        The target DSP (e.g. RX6 or RZ5)

    Returns
    -------
    A subclass instance of :class:`DSPBuffer` containing attributes
    specific to the circuit.
    '''
    # The class factory is a design pattern in object-oriented programming that
    # allows class definitions to be created on-the-fly.  Often we use "static"
    # class definitions (i.e. HardwareBuffer); however, sometimes the definition
    # of the class may depend on a certain "state" at runtime.  A good example
    # of this are RX6 circuits.  We encapsulate each RX6 circuit in it's own
    # class.  The class factory loads the circuit, inspects it to find all tags
    # and what the tag types are.  A class definition is then created with the
    # appropriate properties and methods relevant to that circuit.  This
    # approach is actually very similar to how Python generates the RPcoX and
    # PA5 classes on the fly.

    circuit_path = load_cof(iface, circuit_name)
    # TODO: Need to add a detection routine so that appropriate constants are #
    # initialized at run-time (i.e. if we are using PA5 or RZ5).  properties =
    # RX6_constants

    properties = dict()
    properties['dsp'] = iface
    properties['fs'] = iface.GetSFreq()
    properties['MAX_FREQUENCY'] = properties['fs']/2. # Nyquist frequency
    properties['CIRCUIT_PATH'] = circuit_path

    for key, value in get_tags(iface):
        if key.startswith('%'):
            # These tags are returned by GetNameOf/GetNumOf.  Not really sure
            # what they represent so we ignore them.
            pass
        elif value is None:
            import textwrap
            mesg = """
            Could not determine type for tag %s.  
            
            This often occurs when you link a tag to a port of type Any (e.g.
            the outpout of a Latch).  Use a type converter (e.g. Int2Int or
            Float2Float) to provide the necessary type information.
            """ % key
            mesg = textwrap.dedent(mesg).replace('\n', '')
            raise CircuitError(mesg)
        elif value == np.ndarray:
            # We provide a simple interface to the RX6 buffers via a class
            # that handles the behind-the-scene logics and double-checks
            # boundary conditions (i.e. do we need to wrap around to the
            # beginning of the buffer).  Unfortunately the TDT drivers do not
            # address boundary conditions for us. For example, attempting to
            # write data that is longer than the memory allocated to a SerSource
            # does not raise an error.
            #setattr(circuit, key, DSPBuffer(iface, key))
            properties[key] = DSPBuffer(iface, key)
        elif value == 'static':
            mesg = '%s tag is linked to a static parameter.  Discarding tag.'
            log.debug(mesg, key)
        else:
            #setattr(circuit, key, DSPTag(iface, key))
            properties[key] = DSPTag(iface, key, value)

    return type('circuit.' + circuit_name, (Circuit,), properties)()

from __future__ import division
from cns.buffer import available, BlockBuffer
from cns.util.math import nextpow2
import logging
import numpy as np
from functools import partial
log = logging.getLogger(__name__)

import os, time

from cns.equipment import EquipmentError

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

def convert(src_unit, dest_unit, value, dsp_fs):
    
    def fs_to_nPer(req_fs, dsp_fs):
        # To achieve requested sampling rate, we need
        # to sample every n ticks of the DSP clock.  However, many
        # sampling rates cannot be achieved so we have to coerce
        # sampling rate to the nearest feasible rate.
        if dsp_fs < req_fs:
            raise SamplingRateError(dsp_fs, req_fs)
        return int(dsp_fs/req_fs)
    
    def nPer_to_fs(n, dsp_fs):
        return dsp_fs/n
    
    def n_to_s(n, dsp_fs):
        return n/dsp_fs
    
    def s_to_n(s, dsp_fs):
        return int(s*dsp_fs)
   
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

'''
Many of these buffer functions rely on strict naming conventions to be able to
correctly download data from the DSP.  The conventions are as follows:

    Continuous acquire
        1) <buffer>             name of tag connected to data port of buffer
        2) <buffer>_idx         tag connected to index port of buffer
        3) <buffer>_n           tag connected to size port of buffer
        Each time a read is requested, <buffer>_idx is checked to see if it has
        incremented since the last read.  If it has, the new data is acquired
        and returned.

    Triggered acquire
        1) <buffer>             name of tag connected to data port of buffer
        2) <buffer>_idx_trig    index of last sample buffer acquired prior to
                                the trigger
        3) <buffer>_n           tag connected to size port of buffer
        Each time a read is requested, <buffer>_idx_trig is checked to see if it
        has changed since the last read.  If it has, the new data is
        acquired and returned.  This data should reflect the entire recording
        over a single trigger.
'''

class DSPBuffer(BlockBuffer):
    '''Provides simple read/write access to the DSP buffers.  This class is
    meant to handle the various modes under which data can be stored on the DSP.
    Since data can be compressed for storage in the DSP buffer or it may contain
    multiple channels (stored in 1D format), you must tell the object how to
    interpret the data downloaded from the buffer (e.g. how many channels are
    stored in the buffer, is it compressed, is it set up for continuous or
    triggered acquisition?
    '''

    def __init__(self, dsp, name):
        self.dsp = dsp
        self.name = name
        self.name_len = name + '_n'
        self.max_len = dsp.GetTagSize(name)
        self.length = dsp.GetTagVal(self.name_len)
        BlockBuffer.__init__(self, self.max_len, blocks=2)
        self.initialize()
        self.bind_activex_functions()
        
    def bind_activex_functions(self):
        '''Freezes the Name parameter of the ActiveX function.
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
        """Returns the minimum, maximum valid value, numerical resolution of a
        32-bit float that has been scaled and compressed to an integer for
        faster data streaming."""
        bits = 8*np.nbytes[self.src_type]
        return -(2**bits)/2, (2**bits)/2-1

    def resolution(self):
        return 1/self.sf
    
    def best_sf(self, max_amplitude):
        lb, ub = self.bounds()
        return np.floor(ub/max_amplitude)

    def initialize(self, src_type=np.float32, channels=1, read_mode='continuous', 
                   multiple=1, compression=None, fs=None, sf=1):

        self.__dict__.update(locals())
        
        if read_mode == 'continuous':
            self.name_idx = self.name + '_idx'
        elif read_mode == 'triggered':
            self.name_idx = self.name + '_idx_trig'
        else:
            raise ValueError, '%s read not supported' % read_mode
        
        #self.read_args = type_lookup[src_type], type_lookup[dest_type], 1
        #self._read_f = self.dsp.ReadTagVEX
            
        self.c_factor = int(4/np.nbytes[src_type])
        self.idx = self.dsp.GetTagVal(self.name_idx)
        read_func = self._read_mode[(self.channels==1, self.compression)]
        self._read = read_func.__get__(self, DSPBuffer)
            
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
        try:
            data.fs = self.dsp.GetSFreq()
            self._set_length(len(data))
            self.dsp.WriteTagV(self.name, 0, data.signal)
            log.debug('Set buffer %s with %d samples', self.name, len(data.signal))
        except AttributeError, e:
            print e
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
        # We could use the TDT ReadTagVEX function and pass the appropriate data
        # type parameters (e.g. I8 or I16) and have it expand the 32 bit value
        # to the appropriate number; however, in my tests (see
        # test_readtag_speed.py) it seems pretty clear that TDT uses an
        # inefficient algorithm for converting the data.  If we are converting 4
        # samples of data to 8 bits each then combining it into a 32 bit word,
        # we would expect the read to be 4x faster than the uncompressed version
        # (since we only are transferring 25% of the data); however, the
        # ReadTagVEX function is only 1.16x faster when reading compressed data.
        # If we just grab the raw bits using ReadTagV and use Numpy to convert
        # the 32 bit values to the corresponding 8 bit values, it is 3.8x
        # faster.
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
        data = self._c_read(offset, length)
        temp = np.empty((len(data)/self.channels, self.channels))

        # Since two samples are compressed into a single word before being
        # shuffled, the data is stored in the order A1 A2 B1 B2 C1 C2 D1 D2 A3
        # A4 B3 B4 C3 C4 D3 D4 (where A through D are "channels" and 1 through 4
        # are the sample number).  We need to compensate for this by using some
        # fancy indexing.

        # The TDT ActiveX documentation does not appear to accurately
        # describe how ReadTagVEX works.  ReadTagVEX wants the number of
        # samples acquired, not the buffer index.  If two samples are
        # compressed into a single buffer slot, then we need to multiply
        # the read size by 2.  If four samples are compressed into a
        # single buffer slot, the read size needs to be 4.

        # We also need to offset the read appropriately.  <Don't fully
        # understand this but my test code says I've got it OK>

        # Do not change the four lines below unless you test it with
        # timeit!  This has been optimized for speed.  See
        # test_concatenate_time.py (in the same folder as this file)
        # to see the test results.  This method is an order of a
        # magnitude faster than any other method I have thought of.
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

class NewDSPBuffer(DSPBuffer):
    
    def initialize(self, src_type=np.float32, dest_type=np.float32,
                   channels=1, sf=1, read_mode='continuous', multiple=1,
                   compression=None, fs=None):

        self.__dict__.update(locals())

        if read_mode == 'continuous':
            self.name_idx = self.name + '_idx'
        elif read_mode == 'triggered':
            self.name_idx = self.name + '_idx_trig'
        else:
            raise ValueError, '%s read not supported' % read_mode
        
        self.read_args = type_lookup[src_type], type_lookup[dest_type], channels
        self._read_f = self.dsp.ReadTagVEX
            
        self.c_factor = 4/np.nbytes[src_type]
        self.idx = self.dsp.GetTagVal(self.name_idx)
        
        if self.compression is not None:
            self._read = self._c_read
        else:
            self._read = self._simple_read
        
    def _simple_read(self, offset, length):
        # Available reports the number of samples ready to be read and
        # accounts for various edge cases.  See function documentation for
        # more detail.
        if length == 0:
            return np.array([])
        else:
            print 'offset, length, read_args', offset, length, self.read_args
            data = self._read_f(self.name, offset, length/self.channels, *self.read_args)
            data = np.array(data)
            print data.shape
            return data
        
    def _c_read(self, offset, length):
        data = self._simple_read(offset, length)
        return data/self.sf

    def _mc_c_read(self, offset, length):
        return self._c_read(offset, length)
    
    def _mc_dec_read(self, offset, length):
        return self._c_read(offset, length)
    
class DSPTag(object):
    '''Wrapper around a RPvdsEx circuit tag that facilitates getting and setting
    the value.  If you follow appropriate naming conventions in the DSP circuit,
o   the get and set methods will be able to convert the provided value to the
    appropriate type.  For example, if the DSP tag expects number of samples
    (i.e. cycles of the DSP clock) and you provide the value in seconds, then
    the tag name must be <name>_n (the _n indicates it requires number of
    samples), and you can call circuit.name_n.set(value, src_unit='s').  The
    value you provided will be multiplied by the DSP clock frequency to get the
    appropriate unit which is then uploaded to the DSP.
    '''

    epsilon = 1e-6

    def __init__(self, dsp, name):
        self.dsp = dsp
        self.fs = dsp.GetSFreq()
        self.name = name
        self.unit = name.split('_')[-1]

    def _get_value(self):
        value = self.dsp.GetTagVal(self.name)
        return value

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

    def set(self, value, src_unit=None):
        if src_unit is not None:
            value = convert(src_unit, self.unit, value, self.fs)
        self.value = value

    def get(self, req_unit=None):
        if req_unit is not None:
            return convert(self.unit, req_unit, self.value, self.fs)
        else:
            return self.value

class Circuit(object):
    '''Really, this represents the actual DSP itself, but I call it "circuit"
    (i.e. what the TDT documentation calls the DSP code) since this basically
    allows us to set/get the circuit tag values as well as read from/write to
    the buffers.
    '''
    def reload(self):
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
        if trig == 'A':
            raise NotImplementedError
        elif trig == 'B':
            raise NotImplementedError
        elif type(trig) == int:
            self.dsp.SoftTrg(trig)

    def acquire(self, buffer, samples, trigger=None, timeout=1, dt=0.01):
        self.trigger(trigger)
        cumtime = 0
        idx = self.get(buffer+'_idx')

        while True:
            oldidx, idx = idx, self.get(buffer+'_idx')
            if idx >= samples: break
            elif idx > oldidx: cumtime = 0
            elif timeout is not None and cumtime > timeout:
                raise IOError, 'Read from buffer %s timed out' % buffer
            time.sleep(dt)
            cumtime += dt
        return getattr(self, buffer).read(samples)
    
    def convert(self, src_unit, req_unit, value):
        return convert(src_unit, req_unit, value, self.fs)

def load_cof(iface, circuit_name):
    '''Loads circuit file to DSP device.  Searches cns/equipment/TDT/components directory as well as working directory.'''
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

def get_tags(iface, map=rpcox_types):
    '''Queries RPcoX for information of available tags/variables.
    '''
    num_tags = iface.GetNumOf('ParTag')
    tags = [iface.GetNameOf('ParTag', i+1) for i in range(num_tags)]
    types = [map[iface.GetTagType(tag)] for tag in tags]
    return zip(tags, types)

def circuit_factory(circuit_name, iface, map=rpcox_types):
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
    
    # TODO: most matlab programmers will have no clue what this is doing.  Need
    # to document this better.
    #circuit = type('circuit.' + circuit_name, (Circuit,), properties)()

    for key, value in get_tags(iface):
        if key.startswith('%'):
            # These tags are returned by GetNameOf/GetNumOf.  Not really sure
            # what they represent so we ignore them.
            pass
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
            properties[key] = DSPTag(iface, key)

    return type('circuit.' + circuit_name, (Circuit,), properties)()
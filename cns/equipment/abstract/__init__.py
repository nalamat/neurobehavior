'''The simplest way to connect to a backend is:

from cns import equipment
circuit = equipment.dsp(backend_name).connect(circuit_name, device_name)

This returns an object that allows you to query and set variables in the DSP
code as well as read and write access to the buffers.

Each backend is a collection of classes and functions that generate an
abstraction layer between Python and the backend-specific drivers.  Direct calls
to the backend API is highly discouraged since this means that you will have
difficulty switching to a new backend in the future (e.g. National Instrument's
PXI and FGPA system).

This module describes the expected interface (API) that backends should follow.
'''
from cns.equipment import EquipmentError

def load(circuit, device):
    raise NotImplementedError

def init_device(circuit, device, **kwargs):
    raise NotImplementedError

def set_attenuation(atten, device):
    raise NotImplementedError

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
    
    def nPer_to_fs(nPer, dsp_fs):
        return dsp_fs/nPer
    
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
    '''
    Defines a circuit-specific error.
    '''

class UnitError(CircuitError):
    '''
    Defines an error with converting a unit.
    '''

class SamplingRateError(UnitError):
    '''
    Indicates that the conversion of frequency to sampling rate could not be
    performed.
    '''

    def __init__(self, fs, requested_fs):
        self.fs = fs
        self.requested_fs = requested_fs

    def __str__(self):
        mesg = 'The requested sampling rate, %f Hz, is greater than ' + \
               'the DSP clock frequency of %f Hz.'
        return mesg % (self.requested_fs, self.fs)

class AbstractDSPBuffer(BlockBuffer):
    '''
    Provides simple read/write access to the DSP buffers.  
    
    This class is meant to handle the various methods via which data can be
    stored on the DSP.  Since data can be compressed for storage in the DSP
    buffer and may contain multiple channels, you must tell the object how to
    interpret the data downloaded from the buffer by initializing it via
    :func:`DSPBuffer.initialize`.

    This class relies on strict naming conventions for the DSP variables to
    correctly download data from the DSP.

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

    I have been toying with the idea of creating circuit macros that handle a
    lot of the boilerplate in setting up the necessary tags for the serial
    buffers.  If I do this, then we could incorporate auto-discovery of the
    necessary parameters (e.g. sampling rate, compression settings and number of
    channels) rather than having to hardcode this.
    '''
        
    def __repr__(self):
        return '<%s::%s[idx=%d:len=%d:cyc=%d]>' % \
                (self.__class__.__name__, self.name,
                 self.idx, len(self), self.cycles)
                
    def bounds(self):
        """
        Returns the range of values that can be stored by the buffer's source
        type.

        """
        bits = 8*np.nbytes[self.src_type]
        return -(2**bits)/2, (2**bits)/2-1

    def resolution(self):
        """
        Returns numerical resolution of data given the scaling factor that was
        used to store the data.
        """
        scaling factor the data 
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
        raise NotImplementedError

    def set(self, data):
        '''Writes data to the buffer, starting at index 0 and truncating the
        length of the buffer to the length of the data.

        Parameters
        ----------
            data : array_like or signal
                Data to write to the buffer
        
        Raises
        ------
        * If the data is longer than the maximum length of the buffer

        '''
        raise NotImplementedError

    def write(self, data):
        '''Write data to buffer
        
        Successive calls to write are incremential.  Data is written starting at
        the next available index.
        '''
        try:
            data.fs = self.fs
            super(AbstractDSPBuffer, self).write(data.signal)
        except AttributeError:
            super(AbstractDSPBuffer, self).write(data)

    def samples_processed(self):
        '''Number of new samples in buffer since last read
        '''
        raise NotImplementedError
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
        raise NotImplementedError
    
    def _write(self, offset, data):
        '''Actual implementation of write
        '''

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

class DSPTag(object):
    '''Wrapper around a DSP variabletag that facilitates getting and setting the
    value.  If you follow appropriate naming conventions in the DSP circuit, the
    get and set methods will be able to convert the provided value to the
    appropriate type.  For example, if the DSP tag expects number of samples
    (i.e. cycles of the DSP clock) and you provide the value in seconds, then
    the tag name must be <name>_n (the _n indicates it requires number of
    samples), and you can call circuit.name_n.set(value, src_unit='s').  The
    value you provided will be multiplied by the DSP clock frequency to get the
    appropriate unit which is then uploaded to the DSP.
    '''

    epsilon = 1e-6

    def _get_value(self):
        raise NotImplementedError

    def _set_value(self, value):
        raise NotImplementedError

    value = property(_get_value, _set_value)

    def set(self, value, src_unit=None, lb=-np.inf, ub=np.inf):
        '''The converted value is coerced to the range [lb, ub].  Since lb and
        ub are set to -inf and +inf by default, no coercion is typically done.
        This clipping is useful for some TDT compnents such as TTLDelay2.  If
        N1+N2=0 for TTLDelay2, the component will not relay any TTLs it
        recieves.  By ensuring that N1+N2!=1 when you want a delay of 0, you can
        avoid this issue.  Note that I typically solve this problem by making N1
        configurable via a tag, and setting N2 to 1 that way the software does
        not need to worry about avoiding setting N1 to 0.
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
    '''Acts as a loose wrapper around a RPvdsEx circuit.  The circuit exposes
    the circuit tags (i.e. variables) and buffers as class attributes.
    Technically these attributes are instances of :class:`DSPTag` and
    :class:`DSPBuffer`, respectively.  These instances provide many convenience
    methods and attributes that facilitate coding of software for the RPvdsEx
    circuit.

    This class is not meant to be instantiated directly as a factory function
    must be used to inspect the RPvdsEx circuit, create the appropriate
    :class:`DSPTag` and :class:`DSPBuffer` instances and bind them to the
    Circuit instance.  See :func:`circuit_factory` for more information.
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

    def set(self, tag, value, src_unit=None):
        getattr(self, tag).set(value, src_unit)

    def get(self, tag):
        return getattr(self, tag).value

    def __str__(self):
        return self.__class__.__name__

    def _get_status(self):
        raise NotImplementedError

    def _get_running(self):
        raise NotImplementedError

    running = property(_get_running)
    status = property(_get_status)

    def trigger(self, trig):
        raise NotImplementedError

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

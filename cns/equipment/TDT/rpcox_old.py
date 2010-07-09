from __future__ import division
import logging
log = logging.getLogger(__name__)

import os, time
import numpy as np

from cns.equipment.TDT import buffer

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

from enthought.traits.api import HasTraits, Array, Int, Constant, Bool, Float

rpcox_trait_types = {
        68:     Array,
        73:     Int,
        74:     Constant,
        78:     Bool,
        83:     Float,
        80:     Array,     # This is coefficient buffer?
        65:     None,           # What was this again?
        76:     'Trigger',      # Not sure how to implement this (this is a
                                # software trigger?)
        }

def resolution(type, sf):
    """Returns the minimum, maximum valid value, numerical resolution of a
    32-bit float that has been scaled and compressed to an integer for
    faster data streaming."""
    bits = 8*np.nbytes[type]
    lb, ub = -(2**bits)/2, (2**bits)/2-1
    return lb, ub, 1/sf

class Circuit(object):

    epsilon = 1e-6

    def start(self, trigger=None, **kwargs):
        self.set(**kwargs)
        if trigger is not None:
            self.trigger(trigger)
        self.dsp.Run()

    def set(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def reload(self):
        self.dsp.ClearCOF()
        self.dsp.LoadCOF(self.CIRCUIT_PATH)

    def stop(self):
        self.dsp.Halt()

    def __setattr__(self, name, value):
        if name in self.tags:
            success = self.dsp.SetTagVal(name, value)
            result = self.dsp.GetTagVal(name)
            # Accounts for floating point inaccuracy
            if not result-self.epsilon<value<result+self.epsilon or not success:
                raise SystemError, "Hardware communication error. " + \
                        "Could not set tag %s to %r." % (name, value)
            else:
                log.debug('Set %s to %r', name, value)
        elif name in self.buffers:
            log.debug('setting buffer %s', name)
            self.set_buffer(name, value)
        else:
            object.__setattr__(self, name, value)

    def __getattr__(self, name):
        # Check to see if it is a tag
        if name in self.tags:
            return self.dsp.GetTagVal(name)

        # Check to see if it is a buffer that has been explicitly opened via
        # the open command.  If so, it will return the corresponding generator
        # object.
        try: return self.open_buffers[name]
        except KeyError: pass       # the buffer has not been opened

    def __str__(self):
        return self.__class__.__name__

    def get_status(self):
        # Flip around order of bits so we can walk through them in order
        # bin is a function available only in Python 2.6+
        status = bin(self.dsp.GetStatus())[::-1]
        return status

    def _get_running(self):
        return self.get_status()[2] == '1'

    running = property(_get_running)

    def _get_maxfreq(self):
        return self.fs/2.

    # Returns Nyquist
    MAX_FREQUENCY = property(_get_maxfreq)

    open_buffers = {}
    buffer_pars = {}

    def open(self, name, mode='r', length=None, **kw):
        self.check_buffer(name)
        if mode == 'r':
            pipe = buffer.source(self, name, length, **kw)
            pipe.next() # initialize generator values such as the starting
                        # offset
        elif mode == 'w': pipe = buffer.DSPBuffer(self, name, length, **kw)
        self.open_buffers[name] = pipe
        self.buffer_pars[name] = kw
        return pipe

    def buffer_res(self, name):
        kw = self.buffer_pars[name]
        if kw['compression'] == None:
            return self.epsilon
        else:
            return resolution(kw['src_type'], kw['sf'])[-1]

    def check_buffer(self, buffer, length=0):
        if buffer not in self.buffers:
            raise ValueError, 'Circuit does not have buffer %s' % buffer
        elif length > self.buffer_sizes[buffer]:
            raise ValueError, 'Buffer %s is too small' % buffer

    def get_buffer(self, name, samples, src_type=np.float32,
            dest_type=np.float32):
        '''Assumes data is written starting at the first index of the name.'''
        self.check_buffer(name, samples)
        args = buffer.type_lookup[src_type], buffer.type_lookup[dest_type], 1
        return np.array(self.dsp.ReadTagVEX(name, 0, samples, *args)[0])

    def set_buffer(self, name, data, zero=True):
        '''Assumes data is written starting at the first index of the buffer.'''
        self.check_buffer(name, len(data))
        if zero: self.dsp.ZeroTag(name)
        try: setattr(self, name+'_n', len(data))
        except AttributeError:
            # TODO: SOMETHING INTELLIGENT HERE
            raise
        try:
            # Allows us to pass an instance of a Signal class.  This is an
            # example of "duck" typing.  Rather than checking to see if data is
            # an instance of the Signal class, we just check to see if it has a
            # parameter called signal that is an array.  If that fails (i.e. it
            # will raise an AttributeError, then we just assume that data is an
            # array to be written).
            buffer.set_length(self, name, len(data.signal))
            self.dsp.WriteTagV(name, 0, data.signal)
            log.debug('Set buffer %s with %d samples', name, len(data.signal))
        except AttributeError, e:
            self.dsp.WriteTagV(name, 0, data)
            log.debug('Set buffer %s with %d samples', name, len(data))

    def zero_buffer(self, buffer):
        self.check_buffer(buffer, 0)
        self.dsp.ZeroTag(buffer)

    def buffer_duration(self, buffer):
        return self.buffer_sizes[buffer]/self.fs

    def trigger(self, trig):
        if trig == 'A':
            raise NotImplementedError
        elif trig == 'B':
            raise NotImplementedError
        elif type(trig) == int:
            self.dsp.SoftTrg(trig)

    def acquire(self, buffer, samples, trigger=None, timeout=1):
        self.trigger(trigger)
        dt = 0.01
        cumtime = 0
        idx = getattr(self, buffer+'_idx')

        while True:
            oldidx, idx = idx, getattr(self, buffer+'_idx')
            if idx >= samples: break
            elif idx > oldidx: cumtime = 0
            elif timeout is not None and cumtime > timeout:
                raise IOError, 'Read from buffer %s timed out' % buffer
            time.sleep(dt)
            cumtime += dt
        return self.get_buffer(buffer, samples)

    def sec_to_samples(self, sec):
        return int(sec*self.fs)

    def samples_to_sec(self, samples):
        return samples/self.fs

def load_cof(iface, circuit_name):
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
    
def safe_set(value, iface, tag, epsilon=1e-6):
    success = iface.SetTagVal(name, value)
    result = iface.GetTagVal(name)
    # Accounts for floating point inaccuracy
    if not result-self.epsilon<value<result+self.epsilon or not success:
        raise SystemError, "Hardware communication error. " + \
                "Could not set tag %s to %r." % (name, value)
    else:
        log.debug('Set %s to %r', name, value)
        
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
    # Need to add a detection routine so that appropriate constants are
    # initialized at run-time (i.e. if we are using PA5 or RZ5).
    # properties = RX6_constants
    
    properties = dict()
    properties['dsp'] = iface
    properties['fs'] = iface.GetSFreq()
    properties['CIRCUIT_PATH'] = circuit_path

    def getTags(iface):
        '''Queries RPcoX for information of available tags/variables.
        '''
        num_tags = iface.GetNumOf('ParTag')
        tags = [iface.GetNameOf('ParTag', i+1) for i in range(num_tags)]
        types = [iface.GetTagType(tag) for tag in tags]
        types = [map[t] for t in types]
        return zip(tags, types)

    # Create a 'transparent' interface to the TDT system that makes it very easy
    # and straightforward to interface with these parameters in Python.
    tags = getTags(iface)
    properties['tags'] = []
    properties['buffers'] = []
    properties['buffer_sizes'] = {}
    

    for key, value in tags:
        if key.startswith('%'):
            # These tags are returned by GetNameOf/GetNumOf.  Not really sure
            # what they represent so we ignore them.
            pass
        elif value == np.ndarray:
            # We provide a simple interface to the RX6 buffers via a generator
            # that handles the behind-the-scene logics and double-checks
            # boundary conditions (i.e. do we need to wrap around to the
            # beginning of the buffer).  Unfortunately the TDT drivers do not
            # address boundary conditions for us. For example, attempting to
            # write data that is longer than the memory allocated to a SerSource
            # does not raise an error.
            properties['buffers'].append(key)
            properties['buffer_sizes'][key] = iface.GetTagSize(key)
        elif value == 'static':
            mesg = '%s tag is linked to a static parameter.  Discarding tag.'
            log.debug(mesg % key)
        else:
            #get = lambda: iface.GetTagVal(key)
            #set = lambda: iface.SetTagVal(key)
            #properties[key] = property(get, set)
            #properties[key] = property(get(), set)
            properties['tags'].append(key)

    circuit = type('circuit.' + circuit_name, (Circuit,), properties)()
    return circuit

"""
Primary interface to the equipment (e.g. DSP, pump, attenuator).  This is meant
to be the first step in the "abstraction layer".  Since the libraries are meant
to be usable on computers that may not have all the necessary equipment drivers
installed, the equipment modules are only loaded when requested.

DSP hardware
============

Right now only one DSP backend (TDT) is supported.  A backend module deals with
the hardware and driver-specific implementation details.  For example, to read
from a buffer on a TDT DSP device without using the backend:

>>> from cns.equipment.TDT.actxobjects import RX6
>>> RX6.ConnectRX6('GB', 1)
>>> RX6.ClearCOF()
>>> RX6.LoadCOF('aversive-behavior.rcx')
>>> RX6.Start()
>>> last_read_index = 0
>>> while True:
...     next_index = RX6.GetTagVal('contact_buf_idx')
...     if next_index > last_read_index:
...         length = next_index - last_read_index
...         data = RX6.ReadTagV('contact_buf', last_read_index, length)
...     elif next_index < last_read_index:
...         length_a = RX6.GetTagSize('contact_buf') - last_read_index
...         data_a = RX6.ReadTagV('contact_buf', last_read_index, length_a)
...         data_b = RX6.ReadTagV('contact_buf', 0, next_index)
...         data = np.concatenate(data_a, data_b)
>>>     last_read_index = next_index

Phew!  That was a lot of boilerplate code just to load a circuit, run it, and
continously read any new data in the contact buffer.  You have to continuously
track the last index you read, check to see if the buffer has wrapped around to
the beginning, and acquire the data.  Wouldn't it be easier to just write:

>>> from cns import equipment
>>> circuit = equipment.dsp('TDT').load('aversive-behavior')
>>> circuit.start()
>>> while True:
...     data = circuit.contact_buf.next()

This is precisely how the backend works.  All the hardware-specific
implementation details of how to access the DSP variables (e.g.
contact_buf_idx), determine the buffer size, and read data from the buffer are
handled by `DSPBuffer.read` in the TDT module.  It gets even better.  Let's say
you decide you want to go with National Instruments instead.  Hopefully at some
point, someone has written a backend module for National Instruments (presumably
it would live in the NI module).  In this module there would be a
`DSPBuffer.read` method that knows how to deal with the NI DSP. The only change
you would need to make to your code is to tell it to load the NI module rather
than the TDT module.  

The call to `equipment.dsp()` will load the appropriate backend driver depending
on what's available.  Since each backend driver is expected to follow a set API,
your code should not need to worry about backend-specific implementation details
as long as you restrict yourself to the API.

.. note:: The mechanism for specifying the backend has not really been fleshed
    out (since we only have one supported backend).  Right now you have to
    specify it in the `equipment.dsp` method (it currently defaults to the only
    suported backend, TDT).  However, we could conceivably have a settings file
    for the program that a user can edit to specify the backend, or use an
    environment variable.  Once we need to start supporting additional backends
    (e.g. National Instruments or Neurolarynx), we will have to put some thought
    into the mechanism for loading multiple backends.

Pump hardware
=============

Right now only one pump (New Era) is supported.  I'm going to briefly expand on
how the API abstraction layer is expected to work.  New Era requires a RS-232
cable to communicate with the computer, along with some pretty arcane syntax.
If we wanted to set the infusion rate on the pump, we would need to:

    1. Know how to initialize the serial port, set it's baud rate, and close it
    properly at program exit.
    2. Remember the manufacturer-specific command syntax for setting the rate.
    In this case it's "RAT 0.300 MM<CR>".
    3. Know how to parse the pump's response (which conveys information about
    the status of the pump).

So, we'd need to do:

>>> import serial
>>> pump = serial.Serial(connection_settings)
>>> pump.write("RAT 0.300 MM\n")
>>> result = pump.readline(eol='\x03')

Result is typically an arcane string along the lines of "01I?".  This string
contains a single letter that indicates the status of the pump.  If the string
indicates there is an error, this needs to be converted into something the
Python exception machinery can handle.  We can typically determine what the
error is by inspecting the response string (e.g. a 'S' indicates the pump motor
is stalled) and raising a PumpHardwareError exception that displays a message
that the user can understand.

So, how do we use the API?

>>> from cns import equipment # see a pattern here?
>>> pump = equipment.pump()
>>> pump.rate = 0.3

Better yet, wrap it in a try/except block.

>>> from cns import equipment
>>> try:
...     pump = equipment.pump()
...     pump.rate = 0.3
>>> except PumpCommError:
...     print 'Cannot connect to pump.  Is it turned on?'
>>> except PumpHardwareError:
...     print 'Able to connect to pump, but there is a hardware problem.'

.. note:: 
    Note that `PumpCommError` and `PumpHardwareError` are subclasses of
    `PumpError`.  In turn, `PumpError` is a subclass of `EquipmentError`.  Both
    have subclass-specific error messages.  These error messages should be quite
    informative and contain information to help the user solve the problem (e.g.
    could they have forgotten to turn on something or is a cable disconnected?).
    If the error message isn't very informative, this is considered a BUG and
    should be reported accordingly.  So you could simply do:

    >>> from cns import equipment
    >>> try:
    ...     pump = equipment.pump()
    ...     pump.rate = 0.3
    >>> except EquipmentError, e:
    ...     print e
"""

def dsp(dsp='TDT'):
    '''Load drivers for specified DSP backend and return module that implements
    the `cns.equipment.backend` API.  See `cns.equipment.TDT` for more
    information regarding the API.
    '''
    return __import__(dsp, globals=globals(), level=1)

def pump(pump='new_era'):
    '''Load drivers for specified pump and return module that implements the
    `cns.equipment.pump` API.
    '''
    return __import__(pump, globals=globals(), level=1)

def atten():
    return Attenuator()

class EquipmentError(BaseException):

    def __init__(self, device, mesg):
        self.device = device
        self.mesg = mesg

    def __str__(self):
        return '%s: %s' % (self.device, self.mesg)

class SignalManager(object):

    def __init__(self, signal, buffer):
        self.signal = signal
        self.buffer = buffer

class Attenuator(object):

    max_voltage = 10.0  # Max peak to peak voltage output of system
    max_attenuation = 120.0 # Maximum attenuation of system
    dev_id = 'PA5_1'
    signals = []
    calibration = None

    def initialize(self):
        atten = self.best_atten()
        self.set_atten(atten)
        self.iface.SetAttenuation(atten)

    def set_atten(self, atten):
        self.atten = atten
        for signal in self.signals:
            signal.atten = atten

    def best_atten(self):
        '''Given all the signals registered with the attenuator, determine what
        the maximum attenuation we can set is.'''
        return min([s.pref_atten(self.calibration) for s in self.signals])

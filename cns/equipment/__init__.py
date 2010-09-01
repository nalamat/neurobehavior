"""
Primary interface to the equipment (e.g. DSP, pump, attenuator).  This is meant
to be the first step in the "abstraction layer".  Since the libraries are meant
to be usable on computers that may not have all the necessary equipment drivers
installed, the equipment modules are only loaded when requested.

What is abstraction?
====================

The easiest way to explain this is to illustrate with a short story.  There once
were two labs, one located in a large, bustling city and the other tucked away
on a peaceful country hillside.  They both agreed to use a the same water pump
in their experiments, the Old Northwest 1100.  It was a great pump, but it had
a rather arcane way of controlling it.  Specifically, the computer had to
communicate with this pump via the printer port.  The guy who designed the
interface for the pump was a printer engineer in a previous life, so he stuck
with what he knew.  The labs decided to be thankful the engineer hadn't been an
assembly programmer.

They went on and happily littered their code with various commands to interface
with the pump such as the following snippet:

>>> import parallel
>>> parallel.Parallel(connection_settings)
>>> parallel.write("VOL\\x03\\x03")
>>> response = parallel.readline(eol='\\x03')
>>> if '?' in response:
...     raise SystemError, "The pump is messed up!"
... else:
...     print "Volume infused is " + response[4:10]
        
Everything was great.  They were well on their way to discovering something new,
something exciting.  Something that would have led to a Nature paper.  One day
the folks in the city decided they were sick and tired of the Old Northwest
1100.  It was just too much of a hassle to configure.  They bought a new pump,
the Burlington Northern 5000.  It was one of those that used the latest
technology: fiber optic interfaces, ActiveX drivers, etc.  They hired a Wall
Street programmer to update their code to work with the new pump.  The above
code became:

>>> import win32com
>>> import actxobjects
>>> actxobjects.Pump()
>>> volume = pump.GetVolume(1, "GB")
>>> if volume == NaN:
...     raise SystemError, "The pump is messed up!
... else:
...     print "Volume infused is ", volume

The country folk saw no reason to switch over to this new pump.  It just cost
too much.  Suddenly, the codebase shared by the two labs diverged.  In between
bicycle rides through the rolling hills, the country folk had been adding new,
nifty features to their program.  Stuff like the ability to override the pump's
default behavior during an experiment.  In the meantime, they restructured their
program to make it run faster.  The lab in the city saw the changes and liked
them.  However, when they tried to incorporate the changes, they had to spend
many hours rewriting the pump directives to work with their new pump.  It was a
real pain to remember to update both versions of the program with new features.
Still, they were collecting the data they needed.

Suddenly, the Burlington Northern broke.  They had been in the middle of a
multi-week experiment using a new program to test positive reinforcement.  This
was a program the country lab wasn't using at the moment, so a version designed
to work with the old, reliable Northwest (which they still had laying around in
case their newfangled pump broke) had not been written.  Their programmer was on
vacation (again), so they had to put their experiment on hold until he got back.
In the meantime, another lab in Massachusetts beat them to that Nature paper.

Upon coming back from vacation, he quickly whipped together a hardware
abstraction layer for the two pumps.  These abstraction layers provided a common
interface that the software could use to communicate with the pumps.

>>> from equipment import pump
>>> interface = pump('Burlington')
>>> print "Volume infused is ", interface.volume

The `volume` method knew how to communicate with the specified pump, so the
program did not need to worry about manufacturer specific logic.  If their pump
ever broke again, they could simply tell the software to use the "Old Northwest"
interface instead.  No longer did the labs need to rewrite each other's
enhancements and additions to work with their preferred pump.  It just worked.

DSP hardware
============

How the backends work
---------------------

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
...     last_read_index = next_index
...     if some_condition_met:
...         break
>>> # do something with the data

Phew!  That was a lot of boilerplate code just to load a circuit, run it, and
continously read any new data in the contact buffer.  You have to continuously
track the last index you read, check to see if the buffer has wrapped around to
the beginning, and acquire the data.  Wouldn't it be easier to just write:

>>> from cns import equipment
>>> circuit = equipment.dsp('TDT').load('aversive-behavior')
>>> circuit.start()
>>> while True:
...     data = circuit.contact_buf.next()
...     if some_condition_met:
...         break
>>> # do something with the data

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

What can you expect from a backend?
-----------------------------------

Each backend should, at the minimum, support initializing the DSP and
controller, load a specified circuit and allow the program to read/write to
buffers, get/set tag values and send TTLs.

First, let's load and initialze our backend:

>>> from cns import equipment
>>> dsp = equipment.dsp()
>>> circuit = dsp.load('circuit-name', 'device-name')
>>> circuit.run()

Lets say the circuit has the buffers microphone and speaker as well as the
tags record_duration_n and record_delay_n.  Note that both tag names end in
'_n'.  This is a special naming convention that tells the backend what unit
these tags accept('n' indicates number of ticks of the DSP clock while 'ms'
indicates milliseconds).  The circuit is configured to deliver the data stored
in the speaker buffer to DAC channel 1 (which is connected to a speaker) and
record the resulting microphone waveform.  The entire process is controlled by a
software trigger.

To write a 1 second, 1 kHz tone to the speaker buffer:

>>> from numpy import arange, sin, pi
>>> t = arange(0, dsp.convert('s', 'n', 1))/dsp.fs
>>> waveform = sin(2*pi*1e3*t)
>>> circuit.speaker.write(waveform)

Now we want to configure the microphone to record for a duration of 500 ms with
a 25 ms delay.  Remember that record_delay_n and record_duration_n both require
the number of samples.  Since number of samples depends on the sampling
frequency of the DSP, we would have to compute this:

>>> circuit.record_delay_n.value = int(25e-3*circuit.fs)
>>> circuit.record_duration.value = int(500e-3*circuit.fs)

Alternatively, we can use a convenience method:

>>> circuit.record_delay_n.set(25, src_unit='ms')
>>> circuit.record_duration_n.set(500, src_unit='ms')

Both approaches are fine; however, we recommend that you use the `DSPTag.set`
method rather than computing the value yourself.  This makes the code more
readable.  Now that you've configured the circuit and are ready to record:

>>> import time
>>> circuit.trigger(1)
>>> time.sleep(1)
>>> microphone = circuit.microphone.read()

Alternatively, you can simply use a convenience method, `DSPCircuit.acquire`:

>>> num_samples = circuit.record_duration_n.value
>>> microphone = circuit.microphone.acquire(num_samples, trigger=1, timeout=1)

Pump hardware
=============

How the abstraction layer works
-------------------------------

Right now only one pump (New Era) is supported.  I'm going to briefly expand on
how the API abstraction layer is expected to work.  New Era requires a RS-232
cable to communicate with the computer, along with some pretty arcane syntax.
If we wanted to set the infusion rate on the pump, we would need to:

    1. Know how to initialize the serial port, set it's baud rate, and close it
    properly at program exit.

    2. Remember the manufacturer-specific command syntax for setting the rate.
    Usually it's some string such as "RAT 0.300 MM<CR>".

    3. Know how to parse the pump's response (which conveys information about
    the status of the pump).

So, we'd need to do:

>>> import serial
>>> pump = serial.Serial(connection_settings)
>>> pump.write("RAT 0.300 MM\\n")
>>> result = pump.readline(eol='\\x03')

Result is typically an arcane string along the lines of "01I?".  This string
contains a single letter that indicates the status of the pump.  If the string
indicates there is an error, this needs to be converted into something the
Python exception machinery can handle.  We can typically determine what the
error is by inspecting the response string (e.g. a 'S' indicates the pump motor
is stalled) and raising a PumpHardwareError exception that displays a message
that the user can understand.

So, how do we use the API?
--------------------------

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

Note that `PumpCommError` and `PumpHardwareError` are subclasses of `PumpError`.
In turn, `PumpError` is a subclass of `EquipmentError`.  Both have
subclass-specific error messages.  These error messages should be quite
informative and contain information to help the user solve the problem (e.g.
could they have forgotten to turn on something or is a cable disconnected?).  If
the error message isn't very informative, this is considered a BUG and should be
reported accordingly.  So you could simply do:

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

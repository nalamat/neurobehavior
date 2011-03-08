.. NeuroBehavior documentation master file, created by
   sphinx-quickstart on Tue Aug 17 17:22:45 2010.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. toctree::
    :maxdepth: 2

.. currentmodule: cns.equipment.TDT.rpcox

==============================
Interfacing with the equipment
==============================

Code for loading, initializing and communicating with peripheral hardware
devices lives in :module:`cns.equipment`.  Since the libraries are
meant to be usable on computers that may not have all the necessary equipment
drivers installed, the equipment modules are loaded only when explicitly
requested.

The abstraction layer
=====================

What is abstraction?
--------------------

One way to explain this is to illustrate with a short story.  

There once were two labs, one located in a large, bustling city and the other
tucked away on a peaceful country hillside.  They both agreed to use a the same
water pump in their experiments, the Old Northwest 1100.  It was a great pump,
but it had a rather arcane way of controlling it.  Specifically, the computer
had to communicate with this pump via the printer port.  The guy who designed
the interface for the pump was a printer engineer in a previous life, so he
stuck with what he knew.  The labs decided to be thankful the engineer hadn't
been an assembly programmer.

They went on and happily littered their code with various commands to interface
with the pump such as the following snippet:

>>> import parallel
>>> parallel.Parallel(connection_settings)
>>> parallel.write("VOL\\x03\\x03")
>>> response = parallel.readline(eol='\\x03')
>>> if '?' in response:
...     raise SystemError, "The pump is messed up!"
>>> else:
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
...     raise SystemError, "The pump is messed up!"
>>> else:
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

Backends
========

DSP backend
-----------


Pump backend
------------

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

Note that :class:`PumpCommError` and :class:`PumpHardwareError` are subclasses
of :class:`PumpError`.  In turn, :class:`PumpError` is a subclass of
:class:`EquipmentError`.  Both have subclass-specific error messages.  These
error messages should be quite informative and contain information to help the
user solve the problem (e.g.  could they have forgotten to turn on something or
is a cable disconnected?).  If the error message isn't very informative, this is
considered a BUG and should be reported accordingly.  So you could simply do:

>>> from cns import equipment
>>> try:
...     pump = equipment.pump()
...     pump.rate = 0.3
>>> except EquipmentError, e:
...     print e

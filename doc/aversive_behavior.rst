==========================
Aversive Behavior Paradigm
==========================

Equipment configuration
=======================


Sync trigger
    Connect to trigger in on oscilloscope
    Connect to RZ5 digital 0

    For running behavior paradigms, this trigger is not mandatory.  However, a
    TTL is generated at trial onset that can be used to monitor the waveform on
    the oscilloscope.  When acquiring physiology data, this trigger is
    *mandatory*.  The RZ5 monitors this TTL to determine when a trial has begun.
    
Electrical contact 1
    Connect to the TTL output of the first analog-to-TTL converter

    Make a cable with a BNC connector on one end, with the other end terminating
    in alligator clips for the positive and negative leads.  Connect the
    one clip to the footplate and the other clip to the lick spout (order does
    not matter).  The BNC should be connected to the input of the first
    analog-to-TTL converter.

LED
    Connect to the TTL input of the first power relay input.  Set the power
    relay output to 5 VDC.  Take a Cree XR LED, solder a 1 kOhm resistor into
    the pathway (to limit the current since a LED nominally has zero
    resistance), and wire a BNC connector to the other end.  Be sure to pay
    attention to the positive and negative leads.  Soldering a Cree XR emitter
    requires `advanced soldering techniques`_.

.. _`advanced soldering techniques`: http://www.youtube.com/watch?v=NSxmPGt353I

Optical 1
    This is a two-unit assembly consisting of the infrared LED and a photodiode.
    The IR LED requires a constant-current source (on back).  As with the Cree
    XR emitter, the IR LED has a polarity, so be sure to wire the positive lead
    to the positive terminal of the BNC conenctor.

Shock trigger
    Connect to shock trigger in of the first analog-to-TTL converter
    Connect current control (on back) to remote control of shocker
    Connect current output of shocker to current in (on back)

Electrical contact 2
    See electrical contact 1, except use the second analog-to-TTL converter.

Pump trigger
    Connect to the remote trigger on the pump

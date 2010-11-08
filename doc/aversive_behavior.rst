==========================
Aversive Behavior Paradigm
==========================

Supplies needed
===============

- Cree XR emitter (DigiKey_)
- Optical sensor
    - Infrared LED, OPV380 (DigiKey_)
    - Photodiode, PNZ335-ND (DigiKey_)
- Air puff
    - Pipe adapter 1/8" NPT x 1/4" ID (Cole-Parmer Part #A2-4NP)
    - PVC braided tubing 1/4" ID x 7/16" OD x 3/32" wall (Nalgene Part #8005-0070)
    - Solenoid air control valve 1/8" port (ARO Model #P251SS-012-D via DrillSpot_)

.. _DigiKey: http://digikey.com
.. _DrillSpot: http://www.drillspot.com

Equipment configuration
=======================

========= ======== ======= ============ ==============================
RX6 ID    Bit Mask PP24 ID Connection   Signal
========= ======== ======= ============ ==============================
Bit 0     1        A1      OUT          Sync Trigger
Bit 1     2        A2      IN           
Bit 2     4        A3      OUT          
Bit 3     8        A4      IN           
Bit 4     16       A5      OUT          
Bit 5     32       A6      IN           
Bit 6     64       A7      OUT          Pump trigger
Bit 7     128      A8      OUT          120 VAC relay

Word 1.*  255                           15 for 0-3 bitmask
Word 1.0  1        B1      OUT 5V[*]_   Info light (Cree XR with 1 k|ohm| resistor)
Word 1.1  2        B2      OUT 15V      Bright light (Cree XR with 10|ohm| resistor)
Word 1.2  4        B3      OUT 15V      Air puff (pneumatic solenoid)
Word 1.3  8        B4      OUT          Shock trigger
Word 1.4  16       B5      OUT        
Word 1.5  32       B6      OUT         
Word 1.6  64       B7      OUT        
Word 1.7  128      B8      OUT         

Word 2.*  65280                         3840 for 0-3 bitmask
Word 2.0  256      C1      IN E-ADC[*]_ Electrical sensor 1
Word 2.1  512      C2      IN E-ADC     Electrical sensor 2
Word 2.2  1024     C3      IN O-ADC[*]_ Optical sensor 1
Word 2.3  2048     C4      IN O-ADC     Optical sensor 2
Word 2.4  4096     C5      IN       
Word 2.5  8192     C6      IN        
Word 2.6  16384    C7      IN       
Word 2.7  32768    C8      IN        

.. [*] Pass throught the power relay and set toggle switch to specified voltage.
.. [*] Pass through analog to TTL converter for electrical sensor.
.. [*] Pass output of photosensor through the analog to TTL converter for
       optical sensor.  Be sure to connect the power supply for the LED (on the
       back) to the emitter.

.. |ohm| unicode:: U+003A9  

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

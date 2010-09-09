==========================
Aversive Behavior Paradigm
==========================

Equipment configuration
=======================

====== ======== ======= ========= ======
RX6 ID Bit Mask PP24 ID Direction Signal
====== ======== ======= ========= ======
0      1        1       OUT       Sync Trigger
1      2        2       IN        Electrical contact 1
2      4        3       OUT       LED
3      8        4       IN        Optical 1
4      16       5       OUT       Shock trigger
5      32       6       IN        Electrical contact 2
6      64       7       OUT       Pump trigger
7      128      8       IN        
====== ======== ======= ========= ======

Sync trigger
    Connect to trigger in on oscilloscope
    Connect to RZ5 digital 0

    For running behavior paradigms, this trigger is not needed.  However, when
    monitoring the waveform on the oscilloscope, this TTL output can be used as
    the trigger for the display.  Currently this TTL is generated at the onset
    of the stimulus.  In addition, when acquiring physiology data, the data
    acquisition DSP will monitor this TTL 

Electrical contact 1

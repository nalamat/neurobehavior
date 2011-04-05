============
DSP circuits
============

RepeatPlay
----------

Parameters
^^^^^^^^^^

    out_1
        waveform
    out_2
        waveform

    ttl_1
        array of event times
    ttl_2
        array of event times
    ttl_3
        array of event times
    ttl_4
        array of event times

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

'''

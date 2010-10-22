import sys
from os.path import abspath, dirname, join
libdir = abspath(join(dirname(__file__), '..'))
sys.path.insert(0, libdir)

import logging
log = logging.getLogger()
log.setLevel(logging.DEBUG)
log.handlers.append(logging.StreamHandler())

from cns import equipment

'''
All waveforms uploaded to the DSP buffers must have any necessary onset delays
and intertrial durations included as part of the waveform (e.g. as an array of
zeros).  

This circuit implements a dual-buffer scheme for all buffers.  There is always
one active buffer (a or b) that is being played out.  The other buffer is
considered the reserve buffer and may be safely written to.  Once the data has
been uploaded, fire the appropriate trigger to switch over.  Note that, at
present, you cannot switch buffers individually.  When a switch is requested,
all buffers will switch from a-to-b or b-to-a simultaneously.

...............<============>....................
[ onset delay ][   token    ][   offset delay   ]
[ trial duration                                ]
^ beginning of waveform (e.g. sample 0)
               ^ beginning of token (e.g. sample 160)
                            ^ end of token (e.g. sample 290)
                                                ^ end of waveform

Typically you will want to generate event times (e.g. TTL triggers) during some
feature of the waveform.  There are six TTL buffers available (TTL1 ... TTL6)
that accepts an array of integers.  Each number indicates a sample number
(relative to the beginning of the waveform) at which a TTL should be generated.
The corresponding variable, TTL1_dur_n ... TTL6_dur_n indicates the number of
samples the TTL should be high.  When the buffer becomes active, the first
number in the array is popped.  As soon as the TTL fires, the next number is
removed from the stack.

DSP circuit buffers
-------------------
DACNa and DACNb : array-like
    Token waveforms for speakers 1-2.  Substitute N with the speaker number
    (e.g. DAC1a, DAC2b).
TTLNa and TTLNb : array-like
    Event times (relative to start of trial) for TTLs 1-6.  Substitute N with
    the TTL number (e.g. TTL3a).

DSP circuit variables
---------------------
switch : int
    Bitmask for the TTL that indicates that the circuit may switch buffers
reset : int
    Bitmaks for the TTL that indicates the circuit should reset the sample
    counter and start playing the buffer from the beginning
repetitions : int
    Number of repetitions of the same buffer before the circuit should halt
buffer : int (readonly)
    Active buffer (0=a, 1=b)

DSP circuit triggers
--------------------
soft 1
    Reset circuit immediately but do not switch buffers
soft 2
    Halt circuit
soft 3
    Reset circuit immediately and switch buffers
soft 4
    Switch buffers once switch condition is met
soft 5 through 10
    unused

When searching the parameter space, you would typically write the requested
waveform to the reserve buffer then fire trigger 3 once the data is uploaded.
When presenting a predetermined sequence of waveforms, you would typically write
the next waveform in the sequence to the reserve buffer then fire trigger 4.
Once trigger 4 is fired, you would then have to listen for a change to
`buffer` (which indicates that the buffer has switched over and that you
can now upload the next waveform to the now-reserve buffer).
'''

from cns.signal.type import Tone, AMNoise, Noise, Silence, \
        BandlimitedNoise, FMTone
from cns.signal.util import cos2taper
import time

def demo_preset_sequence(backend='TDT'):
    '''
    This demo explores how we would generate and upload a preset sequence to the
    DSP.  This was mainly motivated out of my concern for ensuring that we could
    present a very rapid sequence of pips (e.g. ABRs are 10 ms pips presented at
    40/sec) with the appropriate event times.  In essence, the way this works is
    we chain together the waveforms for the sequence, upload it as one segment,
    and generate an array of event times for TTL1 that fires at the start of
    each pip.
    '''

    circuit = equipment.dsp(backend).load('output-sequence', 'RX6')
    fs = circuit.fs

    token_duration = 0.005
    trial_duration = 0.010

    from numpy import zeros, concatenate

    signal_sequence = []
    trial_triggers = []
    sequence_triggers = []
    silence = zeros(int((trial_duration-token_duration)*fs))

    # Generate the sequence of pips
    for i in range(5):
        n_ramp = 2
        tone = cos2taper(Tone(duration=token_duration, fs=fs).signal, n_ramp)
        signal_sequence.append(tone)
        signal_sequence.append(silence)
        noise = cos2taper(Noise(duration=token_duration, fs=fs).signal, n_ramp)
        signal_sequence.append(noise)
        signal_sequence.append(silence)
        # Ensure that the trigger fires at the start of each pip
        trial_triggers.append(len(tone)+len(silence))
        trial_triggers.append(len(noise)+len(silence))

    signal_sequence.append(zeros(int(fs)))

    # Concatenate the sequence into a single waveform to be uploaded
    full_waveform = concatenate(signal_sequence)
    sequence_triggers.append(len(full_waveform))

    circuit.start()

    # Upload the data
    circuit.DAC1a.set(full_waveform)
    circuit.TTL1a.set(trial_triggers)
    circuit.TTL3a.set(sequence_triggers)

    # Start running
    circuit.trigger(1)

    # While circuit is playing out first sequence, prepare second sequence
    signal_sequence = []
    trial_triggers = []
    sequence_triggers = []
    silence = zeros(int(1*fs))

    for i in range(25):
        signal = cos2taper(AMNoise(duration=1, env_fm=5,
                           env_depth=1, fs=fs).signal, 250)
        signal_sequence.append(signal)
        trial_triggers.append(len(noise)+len(silence))

    full_waveform = concatenate(signal_sequence)
    sequence_triggers.append(len(full_waveform))

    # Write data to reserve buffers
    circuit.DAC1b.set(full_waveform)
    circuit.TTL1b.set(trial_triggers)
    circuit.TTL3b.set(sequence_triggers)

    # Tell circuit to switch to buffer b and play the new waveform when it's
    # done with the current buffer (i.e. when TTL3 fires).  Note that TTL3 has a
    # bitmask of 000100.  The integer representation of this bitmask is 4.
    circuit.switch.set(4) 
    circuit.trigger(4)

    # When a DSP circuit is first loaded, it registers a program exit hook.
    # When the program exits, it calls this hook to properly shut down the DSP.
    raw_input("Enter to quit")

def demo_mouse_mode(backend='TDT'):
    '''
    This demonstrates the speed at which we can compute a waveform and upload it
    to the DSP when the user requests a change.  In the absence of a GUI, we use
    the command prompt to request the changes.
    '''

    # Load the circuit
    circuit = equipment.dsp(backend).load('output-sequence', 'RX6')
    #from cns.equipment.computer import OutputCircuit
    #circuit = OutputCircuit()
    circuit.start() # Note that circuit is still in paused state
    fs = circuit.fs

    token_delay = 0
    token_duration = 5
    trial_duration = 7

    circuit.trigger(1)

    # Reset when TTL1 fires
    circuit.reset.set(1)
    # Switch when TTL1 fires
    circuit.switch.set(1)

    import textwrap
    mesg = textwrap.dedent("""
    Signal types (or q to quit):
    1. Tone
    2. Noise
    3. AM Noise
    4. Bandlimited Noise
    5. Set to changeover immediately
    6. Set to changeover at end of trial
    """)

    mode = 3

    def set_signal(signal):
        from numpy import zeros, r_, array

        # Apply tapered envelope to minimize spectral splatter
        signal = cos2taper(signal.signal, int(0.1*fs))
        pad_pre = zeros(int(token_delay*fs))
        pad_post = zeros(int((trial_duration-token_delay-token_duration)*fs))

        # First, check to see which buffer is current and write data to the
        # reserve buffer.  Once the data is written, send a software trigger 
        # to tell the circuit to switch to the new buffer.  When mode == 3,
        # circuit switches immediately, when mode == 4, circuit switches when
        # switch condition is met.
        if circuit.buffer.value == 1:
            circuit.DAC1a.set(signal)
            circuit.TTL1a.set([len(signal)]) # Fire TTL1 at end of waveform
        else:
            circuit.DAC1b.set(signal)
            circuit.TTL1b.set([len(signal)]) # Fire TTL1 at end of waveform
        circuit.trigger(mode) 
        # Note that because circuit resets on TTL1 and TTL1 fires at the end of
        # the waveform, the circuit will wrap to the beginnign of the waveform
        # and start playing it out again.  If TTL1 fired halfway through the
        # waveform, it would be truncated and the playout would start at the
        # beginning.

    # See cns.signal.type.* for the code that generates these waveforms
    while True:
        response = raw_input(textwrap.dedent(mesg))
        if response == 'q':
            break
        elif response == '0':
            # Yes a secret option!!!
            set_signal(FMTone(fc=1000, fm=2, delta_fc_max=500,
                              duration=token_duration, fs=fs))
        elif response == '1':
            set_signal(Tone(frequency=1000, duration=token_duration, fs=fs))
        elif response == '2':
            set_signal(Noise(duration=token_duration, fs=fs))
        elif response == '3':
            set_signal(AMNoise(duration=token_duration, env_fm=5, env_depth=1,
                fs=fs))
        elif response == '4':
            set_signal(BandlimitedNoise(duration=token_duration, fs=fs))
        elif response == '5':
            mode = 3
        elif response == '6':
            mode = 4
        else:
            print "Invalid option"

# Python files can either be imported as part of another program or executed
# directly via the command line.  __name__ is a variable available to every
# script that tells the script whether it is being launched directly or being
# imported by another program.
# 
# This is a very neat trick for testing code.  If you are writing a module of
# functions you can write some test or demo functions that are run whenever you
# execute the file directly, but not when you import the functions for use by
# another script.
#
# >>> if __name__ == '__main__':
# >>>     run_demo_code()
# >>>     run_test_code()

if __name__ == '__main__':
    import sys, cProfile
    if len(sys.argv) == 2:
        exec_statement = '%s("TDT")' % sys.argv[1]
    elif len(sys.argv) == 3:
        exec_statement = '%s("%s")' % tuple(sys.argv[1:])
    else:
        print 'usage: play_signals_v2.py <function> <backend>'
        sys.exit()

    #print exec_statement
    cProfile.run(exec_statement, 'profile')
    #import pstats
    #p = pstats.Stats('profile')
    #p.strip_dirs().sort_stats('cumulative').print_stats(20)

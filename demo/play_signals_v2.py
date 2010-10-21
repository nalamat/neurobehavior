import sys
from os.path import abspath, dirname, join
libdir = abspath(join(dirname(__file__), '..'))
sys.path.insert(0, libdir)

import logging
log = logging.getLogger()
log.setLevel(logging.DEBUG)
log.handlers.append(logging.StreamHandler())

from cns import equipment

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

from cns.signal.type import Tone, AMNoise, Noise, Silence, BandlimitedNoise
from cns.signal.util import cos2taper
import time

def main_sequence():
    circuit = equipment.dsp('TDT').load('output-sequence', 'RX6')
    fs = circuit.fs

    token_duration = 0.005
    trial_duration = 0.010

    from numpy import zeros, concatenate

    signal_sequence = []
    trial_triggers = []
    sequence_triggers = []
    silence = zeros(int((trial_duration-token_duration)*fs))

    for i in range(5):
        n_ramp = 2
        tone = cos2taper(Tone(duration=token_duration, fs=fs).signal, n_ramp)
        signal_sequence.append(tone)
        signal_sequence.append(silence)
        noise = cos2taper(Noise(duration=token_duration, fs=fs).signal, n_ramp)
        signal_sequence.append(noise)
        signal_sequence.append(silence)
        trial_triggers.append(len(tone)+len(silence))
        trial_triggers.append(len(noise)+len(silence))

    signal_sequence.append(zeros(int(fs)))

    full_waveform = concatenate(signal_sequence)
    sequence_triggers.append(len(full_waveform))

    circuit.start()


    circuit.DAC1a.set(full_waveform)
    circuit.TTL1a.set(trial_triggers)
    circuit.TTL3a.set(sequence_triggers)
    print trial_triggers
    print sequence_triggers

    circuit.trigger(1) # Apply changes and start

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

    # Changeover when TTL3 fires
    circuit.switch.set(4) 
    circuit.trigger(4)

    #while 1:
        #print "A", circuit.TTL1a_value.value
        #print "B", circuit.TTL3a_value.value

    raw_input("Enter to quit")

def main():
    #---------------------------------------------------------------------------
    # Load the circuit
    #---------------------------------------------------------------------------

    #---------------------------------------------------------------------------
    # Configure circuit defaults
    #---------------------------------------------------------------------------
    '''
    The DSP circuit has

    DSP circuit paramters
    ---------------------
    Trial structure
        token_del   ---------
        token_dur            <=========>
        post_del                        ----------------
        trial_dur   ------------------------------------

    reps : int
        Number of times to repeat buffer (-1=continuous)
    token_dur_n : int
        Duration of sound token in samples.  Typically this should be set to the
        length of the waveform.
    token_del_n : int
        Number of samples to delay sound token.  This is typicaly used when you
        want to generate some event (e.g. a NMR pulse) before the token is
        played.
    rep_dur_n : int
        Duration of the entire trial.  Includes token_del_n and token_dur_n.
        Note that post_del (the silent period following presentation of the
        sound token) is implicit in rep_dur_n-(token_del_n+token_dur_n).
    buffer : int (read only)
        Indicates active buffer, 0 = a, 1 = b

    It is your responsibility to ensure that (token_del + token_dur) >=
    trial_dur.

    All of these variables are guarded by latches.  Their values will not be
    applied until you fire a software trigger (2 or 3).  See the section on DSP
    circuit triggers for more information.

    DSP circuit buffers
    -------------------
    This circuit implements a dual-buffer scheme for all buffers.  There is
    always one active buffer (a or b) that is being played out.  The other
    buffer is considered the reserve buffer and may be safely written to.  Once
    the data has been uploaded, fire the appropriate trigger to switch over.
    Note that, at present, you cannot switch buffers individually.  When a
    switch is requested, all buffers will switch from a to b or b to a
    simultaneously.
    
    DACNa and DACNb : array-like
        Token waveforms for speakers 1-2.  Substitute N with the speaker number
        (e.g. DAC1a, DAC2b).
    TTLNa and TTLNb : array-like
        Event times (relative to start of trial) for TTLs 3-6.  Substitute N
        with the TTL number (e.g. TTL3a).  Note that the first two TTLs are
        reserved.

    DSP circuit triggers
    --------------------
    soft 1
        Unpause (note that when loaded, circuit is in a paused state so this
        trigger must be fired once you've configured the circuit)
    soft 2
        Switch buffers and apply new parameters now
    soft 3
        Apply new parameters now, but don't switch buffers
    soft 4
        Switch buffers and apply new parameters when current trial is over
    soft 5
        Apply new parameters when current trial is over, but don't switch
        buffers
    soft 6
        Pause
    soft 7 through 10
        unused

    Triggers 2 and 3 end the current trial and apply the requested changes
    immediately.  Triggers 4 and 5 will apply the requested changes once the
    current trial is over.  When searching the parameter space, you would
    typically write the new waveform to the reserve buffer then fire trigger 2
    once the data is uploaded.  When presenting a predetermined sequence of
    waveforms, you would typically write the next waveform in the sequence to
    the reserve buffer then fire trigger 4.  Once trigger 4 is fired, you would
    then have to listen for a change to circuit.buffer (which indicates that the
    buffer has switched over and that you can now upload the next waveform to
    the now-reserve buffer).
    
    TODO: This dual-buffer paradigm seems to work fine for long-duration tokens.
    However, I need to test this with shorter-duration tokens (e.g. total trial
    duration 25 ms).

    '''

    circuit = equipment.dsp('TDT').load('output-sequence', 'RX6')
    circuit.start() # Note that circuit is still in paused state
    fs = circuit.fs

    #---------------------------------------------------------------------------
    # Play!!!!
    #---------------------------------------------------------------------------
    token_delay = 0
    token_duration = 1
    trial_duration = 2

    circuit.trigger(1)

    circuit.reset.set(1)
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
        # Apply tapered envelope to minimize spectral splatter
        from numpy import zeros, r_, array

        signal = cos2taper(signal.signal, int(0.1*fs))

        pad_pre = zeros(int(token_delay*fs))
        pad_post = zeros(int((trial_duration-token_delay-token_duration)*fs))

        signal = r_[pad_pre, signal, pad_post]

        # This circuit implements a dual-buffer scheme.  It will continue to
        # play data from one buffer until it recieves a trigger to switch to the
        # new buffer.  The buffers are named DAC1a and DAC1b.  First, check to
        # see which buffer is current and write data to the reserve buffer.
        # Once the data is written, send a software trigger (2) to tell the
        # circuit to switch to the new buffer.
        if circuit.buffer.value == 1:
            circuit.DAC1a.set(signal)
            circuit.TTL1a.set([len(signal)])
        else:
            circuit.DAC1b.set(signal)
            circuit.TTL1b.set([len(signal)])
        circuit.trigger(mode) 

    while True:
        response = raw_input(textwrap.dedent(mesg))
        if response == 'q':
            break
        elif response == '1':
            set_signal(Tone(frequency=5000, duration=token_duration, fs=fs))
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

if __name__ == '__main__':
    import cProfile
    cProfile.run('main_sequence()', 'profile')
    import pstats
    p = pstats.Stats('profile')
    p.strip_dirs().sort_stats('cumulative').print_stats(20)

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

def main():
    #---------------------------------------------------------------------------
    # Load the circuit
    #---------------------------------------------------------------------------
    circuit = equipment.dsp('TDT').load('output', 'RX6')
    fs = circuit.fs

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

    token_duration = 10
    trial_duration = 11
        
    # Set DSP variable to the exact value
    circuit.reps.value = -1 # repeat forever
    circuit.token_del_n.value = 0 # no token delay
    # Convert 5 sec to number of samples and set tag value.  If sampling
    # frequency is 98,321, rep_dur_n will be set to int(5*98,321)
    circuit.trial_dur_n.set(trial_duration, src_unit='s') 
    circuit.token_dur_n.set(token_duration, src_unit='s') 

    #---------------------------------------------------------------------------
    # Play!!!!
    #---------------------------------------------------------------------------
    circuit.start()
    # Note that circuit is still in paused state

    import textwrap
    mesg = textwrap.dedent("""
    Signal types (or q to quit):
    1. Tone
    2. Noise
    3. AM Noise
    4. Bandlimited Noise
    5. Change intertrial duration
    """)

    def set_signal(signal):
        # Apply tapered envelope to minimize spectral splatter
        signal = cos2taper(signal.signal, int(0.1*fs))

        # This circuit implements a dual-buffer scheme.  It will continue to
        # play data from one buffer until it recieves a trigger to switch to the
        # new buffer.  The buffers are named DAC1a and DAC1b.  First, check to
        # see which buffer is current and write data to the reserve buffer.
        # Once the data is written, send a software trigger (2) to tell the
        # circuit to switch to the new buffer.
        if circuit.buffer.value == 1:
            circuit.DAC1a.set(signal)
        else:
            circuit.DAC1b.set(signal)
        circuit.trigger(2) # Apply change now!

    while True:
        response = raw_input(textwrap.dedent(mesg))
        if response == 'q':
            break
        elif response == '1':
            set_signal(Tone(frequency=5000, duration=duration, fs=fs))
        elif response == '2':
            set_signal(Noise(duration=duration, fs=fs))
        elif response == '3':
            set_signal(AMNoise(duration=duration, env_fm=5, env_depth=1, fs=fs))
        elif response == '4':
            set_signal(BandlimitedNoise(duration=duration, fs=fs))
        elif response == '5':
            mesg = "Enter new intertrial duration (current: %.2f)" \
                    % trial_duration
            try:
                dur = float(raw_input(mesg))
                if dur < token_duration:
                    mesg = "Trial duration must be greater than %.2f" \
                            % token_duration
                    raise ValueError(mesg)
                circuit.trial_dur_n.set(dur, src_unit='s')
                # apply change to parameter but don't switch buffer
                circuit.trigger(3) 
            except ValueError, e:
                print str(e)
        else:
            signal = Silence(duration=duration, fs=fs)

if __name__ == '__main__':
    import cProfile
    cProfile.run('main()', 'profile')
    import pstats
    p = pstats.Stats('profile')
    p.strip_dirs().sort_stats('cumulative').print_stats(20)

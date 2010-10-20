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
from cns.signal.util import taper

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
    reps : int
        Number of times to repeat buffer.  -1 is infinite.
    rep_dur_n : int
        Controls trial duration (a trial is defined as the start of the signal
        to the start of the next signal)
    buf : int
        The DSP is set up under a two-buffer scheme, A & B, where you can write
        to one buffer while the other buffer is being played out.  Indicates
        which buffer to use (0=A, 1=B).
    '''

    duration = 10
        
    # set tag value to that exact number.
    #circuit.reps.value = -1 
    # Convert 5 sec to sample number and set tag value.  If sampling frequency
    # is 98,321, rep_dur_n will be set to int(5*98,321)
    circuit.rep_dur_n.set(duration+1, src_unit='s') 
    circuit.sw_dur_n.set(duration, src_unit='s') 

    #---------------------------------------------------------------------------
    # Play!!!!
    #---------------------------------------------------------------------------
    circuit.start()

    import textwrap
    mesg = textwrap.dedent("""
    Signal types (or q to quit):
    1. Tone
    2. Noise
    3. AM Noise
    4. Bandlimited Noise
    """)

    while True:
        response = raw_input(textwrap.dedent(mesg))
        if response == 'q':
            break
        # Configure buffer for speaker 1
        elif response == '1':
            signal = Tone(frequency=5000, duration=duration, fs=fs)
        elif response == '2':
            signal = Noise(duration=duration, fs=fs)
        elif response == '3':
            signal = AMNoise(duration=duration, env_fm=5, env_depth=1, fs=fs)
        elif response == '4':
            signal = BandlimitedNoise(duration=duration, fs=fs)
        else:
            signal = Silence(duration=duration, fs=fs)

        signal = taper(signal.signal, 'cosine squared', int(0.1*fs))

        # Check to see which buffer is current and write data to the reserve
        # buffer.  Software trigger 1 tells the circuit to switch to the new
        # buffer.
        if circuit.buffer.value == 1:
            circuit.DAC1a.set(signal)
        else:
            circuit.DAC1b.set(signal)
        circuit.trigger(1)

if __name__ == '__main__':
    import cProfile
    cProfile.run('main()', 'profile')
    import pstats
    p = pstats.Stats('profile')
    p.strip_dirs().sort_stats('cumulative').print_stats(20)

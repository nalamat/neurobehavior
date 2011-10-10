from calibrate import spec_cal, plot_cal
from pylab import show
from signal_types import chirp

def compare_speakers():
    sig = chirp(DAQ.fs, 100, DAQ.MAX_FREQUENCY, 10)
    colors = ['g', 'r', 'k', 'b', 'y', 'o']

    i = 0
    results = []
    while True:
        speaker = raw_input('Speaker Name: ').strip()
        if speaker == '':
            break
        else:
            result = spec_cal(sig, 50, 10)
            plot_cal(result, colors[i], speaker)
            results.append(result)
            i += 1
    return results

if __name__ == '__main__':
    results = compare_speakers()
    show()

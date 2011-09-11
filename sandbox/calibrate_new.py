from __future__ import division

from tdt import DSPCircuit
from enthought.traits.api import HasTraits, String, CFloat
from scipy.signal import butter, filtfilt, hann
import logging
import numpy as np

from os.path import join
from cns import get_config

#logging.setLevel(logging.DEBUG)
log = logging.getLogger(__name__)

#DAQ = equipment.dsp()

#DAQ_SETTINGS = {
#        'circuit':          'PlayRecord',
#        'device':           'RX6',
#        'ch_DAC':           DAQ.RX6_OUT1,
#        'ch_ADC':           DAQ.RX6_IN2,
#        }
def dbtopa(db):
    return 10**(db/20.0)

def dbspltopa(db):
    return dbtopa(db)*2e-5

def rms(waveform):
    return np.mean(waveform**2)**0.5

def fft_analyze(signals, fs, mic_sens=None, filter=None):
    if filter is not None:
        signals = [filtfilt(x=s, **filter) for s in signals]

    transforms = [rfft(fs, s) for s in signals]
    freq, power, phase = zip(*transforms)
    signal = np.array(signals).mean(0)

    if mic_sens is not None: power = patodb(np.array(power).mean(0) / mic_sens)
    else: power = np.array(power).mean(0)

    result = {
            't':            np.arange(len(signal)) / fs,
            'signal':       signal,
            'signals':      signals,
            'frequencies':  freq[0],
            'power':        power,
            'phase':        np.array(phase).mean(0),
            }
    return result

def inst_power(signal, window):
    # Normalize the window for a running average
    window = window / window.sum()
    return np.convolve(signal ** 2, window) ** 0.5

def spl_analyze(signal, window, fs, sens=0.0015):
    power = inst_power(signal, window)
    if sens is not None:
        power = patodb(power / sens)
    t = np.arange(len(power)) / fs
    return t, power

def tone_frequency(fs, waveform, frequency):
    n = np.arange(len(waveform))/fs
    w = 2*np.pi*frequency
    vector = np.sum(waveform*np.exp(-1j*w*n))
    return np.abs(vector), np.angle(vector)

def ref_cal(duration=1, averages=2, ref_freq=1e3, ref_level=93.8, gain=20,
        fft=False, mode='conv'):
    '''
    Calibrates measuring microphone against a known reference (e.g. a
    pistonphone).  Typically this is the B&K microphone, but certainly could be
    any microphone that is felt to produce a flat frequency response across the
    range of frequencies of interest.

    TODO: Update this so it incorporates the actual B&K calibration file
    (where do we get this?).

    level           Output of reference in dB SPL
    frequency       Frequency of reference in Hz

    verbose         Returns signal and FFT so it can be plotted
    '''

    circuit_path = join(get_config('RCX_ROOT'), 'play_record.rcx')
    circuit = DSPCircuit(circuit_path, 'RZ6')
    circuit.start(1)
    samples = circuit.convert(duration, 's', 'nPow2')

    # Important, rec_delay must be at least 1 or the circuit will not work
    circuit.set_tags(play_duration=0, rec_duration=samples, rec_delay=1)
    mic_buffer = circuit.get_buffer('mic', 'r')
    mic_data = mic_buffer.acquire_samples(1, samples, 1)
    print rms(mic_data)
    print tone_frequency(circuit.fs, mic_data[0].ravel(), 1e3)
    from pylab import plot, show
    plot(mic_data[0].ravel()[:5e3])
    show()
    return
    print mic_data.shape
    if circuit.get_tag('clipped'):
        print 'Clipping occured'
    for m in mic_data:
        #rms = np.mean(m.ravel()**2)**0.5
        magnitude, phase = tone_frequency(circuit.fs, m, 1e3)
        print magnitude/dbspltopa(ref_level+gain)
    #plot(mic_data[0].ravel())
    #show()
    return mic_data

    #print mic_data.shape
    return

    # Do the calibration!
    #result = tone_power(device, samples, averages=averages, freq=ref_freq,
    #                    fft=fft, mode=mode)

    log.debug('Measured %.2f Vrms at %.2f Hz from the pistonphone' % \
            (result[0], ref_freq))

    sens = result[0] / dbtopa(ref_level)

    debug_mesg = 'Using the pistonphone reference of %.2f dB SPL, ' + \
            'microphone sensitivity is %.4f Vrms/Pa'
    log.debug(debug_mesg % (ref_level, sens))

    # Phase is meaningless since we have little control over the pistonphone, so
    # we do not return this, just microphone sensitivity.
    if fft: return sens, result[-1]
    else: return sens

def tone_cal(freq, duration=.25, rec_delay=0.1, mic_sens=0.0015,
        atten=10, fft=False, **kw):

    if not rec_delay > 0:
        raise ValueError("Delay of recording must be greater than zero")

    # We need to initialize device so we can obtain certain parameters from it
    # (specifically the sampling frequency).
    device = DAQ.init_device(**DAQ_SETTINGS)

    samples = device.convert('s', 'nPow2', duration)
    rec_delay_samples = device.convert('s', 'n', rec_delay)
    play_samples = samples + rec_delay_samples * 2
    play_dur = device.convert('s', 'n', play_samples)
    tone = Tone(frequency=freq, fs=device.fs, duration=play_dur, amplitude=1)

    device.configure(play_duration=play_samples, rec_duration=samples,
            rec_delay=rec_delay_samples, signal=tone.signal)

    # Prepare equipment for recording
    equipment.dsp().PA5.SetAtten(atten)

    result = tone_power(device, samples, freq=freq, fft=fft, **kw)
    spl = patodb(result[0] / mic_sens) + atten

    if len(result) == 3:
        phase, fft_data = result[-2:]
        fft_data['power'] = patodb(fft_data['power'] / mic_sens)
        return spl, phase, fft_data
    else:
        return spl, result[1]

def spec_cal(signal, averages=1, atten=20, mic_sens=0.015, filter=None):
    #equipment.backend.PA5.SetAtten(atten)
    DAQ.PA5.SetAtten(atten)
    device = DAQ.init_device(**DAQ_SETTINGS)
    signal.fs = device.fs
    device.configure(signal=signal, play_duration=len(signal),
            rec_duration=len(signal) + 100)
    signals = acquire(device, len(signal) + 100, averages)
    #print 'filtering'

    return fft_analyze(signals, device.fs, mic_sens, filter=filter)

def level_cal(signal, averages=1, atten=20, mic_sens=3.59e-3):
    DAQ.PA5.SetAtten(atten)
    device = DAQ.init_device(**DAQ_SETTINGS)
    device.signal.initialize()
    device.signal.set(signal)
    device.configure(play_duration=len(signal),
                     rec_duration=len(signal) + 100)
    signals = acquire(device, len(signal) + 100, averages)

    #b, a = butter(1, 100/device.fs, btype='high')
    b, a = butter(4, (np.pi * 1e3 / device.fs, np.pi * 3e3 / device.fs), btype='bandpass')
    signals = [filtfilt(b, a, s) for s in signals]

    signal = np.array(signals).mean(0)
    window = hann(device.fs * 5e-3)
    return spl_analyze(signal, window, device.fs, mic_sens)

def plot_cal(results, *args, **kw):
    from pylab import subplot, show
    fft_plot = subplot(111)
    fft_plot.semilogx(results['frequencies'], results['power'], *args, **kw)
    fft_plot.set_xlabel('Frequency (Hz)')
    #fft_plot.set_ylabel('Amplitude (dB)')
    show()

def swept_cal(frequencies, **kw):
    result = [tone_cal(f, **kw) for f in frequencies]
    amplitude, phase = zip(*result)
    return amplitude, phase

def test_chirp(aves, atten):
    sig = chirp(DAQ.fs, 100, e3, 10)
    spec_cal(sig, aves, atten)

def compare_sweep_chirp():
    freqs = np.arange(1e3, 2e3, 100)
    sig = chirp(DAQ.fs, 100, DAQ.MAX_FREQUENCY, 10)
    chirp_result = spec_cal(sig, 50, 10)
    sweep_result = swept_cal(freqs, 30)[-1]
    plot_cal(chirp_result, 'r', 'Chirp')
    plot_cal(sweep_result, 'k', 'Sweep')
    show()

def compare_tone_fm_am():
    pass

    #from cns.signal.type import Tone, AMTone, FrequencyModulation, AMNoise
    #f = 2e3
    #dur = 1
    #a = 1
    #atten = 30
    #tone = Tone(frequency=f, duration=dur)
    #am = AMTone(frequency=f, envelope_fm=5, envelope_depth=0.1, duration=dur)
    ##am = AMNoise(envelope_fm=5, envelope_depth=0.2, duration=dur)
    #fm = FrequencyModulation(fc=f, fm=5, delta_fc_max=15, duration=dur)

    #t_tone, tone_power = level_cal(tone, averages=a, atten=atten)
    #t_am, am_power = level_cal(am, averages=a, atten=atten)
    #t_fm, fm_power = level_cal(fm, averages=a, atten=atten)

    #from pylab import figure, plot, show
    #figure()
    #plot(t_tone, tone_power, 'k', label='Tone')
    #plot(t_am, am_power, 'r', label='AM')
    #plot(t_fm, fm_power, 'g', label='FM')
    #show()

ref_cal()

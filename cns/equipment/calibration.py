'''
Created on Mar 29, 2010

@author: Brad Buran
'''

import numpy as np

from enthought.traits.api import HasTraits, Str, Float, Any, Property, \
        Instance,  Array, Tuple, Enum, Trait
from enthought.traits.ui.api import View, Item, VGroup

class Standard(HasTraits):

    manufacturer = Str
    ID = Any('')
    frequency = Float(units='Hz')
    level = Float(units='dB SPL')

    def __str__(self):
        return '{manufacturer} {ID} ({level} dB SPL @ {frequency} Hz)'.format(**self.__dict__)

class Microphone(HasTraits):

    manufacturer = Str
    ID = Any
    nominal_sens = Trait(None, Float(units='Vrms/Pa'))
    actual_sens = Float(units='Vrms/Pa')
    #frequency_range = Tuple(Float, Float)

    def __str__(self):
        if self.nominal_sens is not None:
            return '{manufacturer} {ID} ({nominal_sens} Vrms/Pa)'.format(**self.__dict__)
        else:
            return '{manufacturer} {ID}'.format(**self.__dict__)

class Speaker(HasTraits):

    manufacturer = Str
    part_number = Any
    ID = Any
    frequency_range = Tuple(Float, Float)

    def __str__(self):
        return '{manufacturer} {ID} ({part_number})'.format(**self.__dict__)

# Microphones
MICROPHONE_OPTIONS = [
    #Microphone(manufacturer='Custom', ID=''),
    Microphone(manufacturer='B&K', ID=4135, nominal_sens=59e-3),
    Microphone(manufacturer='B&K', ID=4134, nominal_sens=11.6e-3),
    Microphone(manufacturer='B&K', ID=4133, nominal_sens=12.5e-3), ]

STANDARD_OPTIONS = [
    None,
    Standard(manufacturer='B&K', ID=4230, frequency=1e3, level=93.8),
    Standard(manufacturer='B&K', ID=4228, frequency=250, level=124),]

SPEAKER_OPTIONS = [
    Speaker(manufacturer='Vifa', part_number='DX25TG05-04', ID=1),
    Speaker(manufacturer='Madisound crossover', part_number='custom', ID='1') ]

calibration_view = View(
    VGroup(
        'standard',
        'microphone',
        Item('object.microphone.actual_sens',
             enabled_when='standard is None',
             label='Microphone sensitivity (Vrms/Pa)'),
        'speaker',
        label='Hardware configuration'))

class MicrophoneCalibration(HasTraits):
    
    microphone  = Enum(MICROPHONE_OPTIONS)
    standard    = Trait(None, Enum(STANDARD_OPTIONS))
    
    duration = Float(2)
    averages = Float(1)
    
    waveforms = Array
    fft = Array
    
class SpeakerCalibration(HasTraits):

    speaker = Enum(SPEAKER_OPTIONS)
    microphone = Enum(MICROPHONE_OPTIONS)

    attenuation = Float
    amplifier_gain = Float
    tone_amplitude = Float

    data = Array

    frequency = Property
    magnitude = Property
    phase = Property

    lower_frequency = Float
    upper_frequency = Float
    frequency_step = Float

    def _get_frequency(self):
        return self.data.frequency

    def _get_magnitude(self):
        return self.data.magnitude

    def _get_phase(self):
        return self.data.phase

    def _get_maxspl(self):
        return self.data.magnitude + self.attenuation

    def get_magnitude(self, frequencies):
        return np.interp(frequencies, self.frequency, self.magnitude,
                         right=np.nan, left=np.nan)

    def get_phase(self, frequencies):
        return np.interp(frequencies, self.frequency, self.phase,
                         right=np.nan, left=np.nan)
        
    traits_view = View('microphone',
                       Item('standard', label='Pistonphone'),
                       'speaker')
    
class CalibrationView(HasTraits):

    calibration = Instance(Calibration, ())
    actual_sens = Float
    
    traits_view = View(
            Item('calibration', style='custom', show_label=False),
            Item('actual_sens', label='Microphone sens (Vrms/Pa)'))

def acquire(dev, samples, n):
    signals = [dev.acquire(dev.mic, samples, trigger=1) for i in range(n)]
    if dev.clipped.value:
        # TODO: this could be revised a bit to be more informative
        raise SystemError, 'Clipping of signal'
    return signals

def tone_power(dev, samples, averages=2, freq=1e3, mode='conv', fft=False):
    '''Calibrates measuring microphone against a known reference (e.g. a
    pistonphone).  Typically this is the B&K microphone, but certainly could be
    any microphone that is felt to produce a flat frequency response across the
    range of frequencies of interest.

    samples         Number of samples to acquire
    averages        Number of samples to average.
    freq            Frequency to extract

    DEBUGGING PARAMETERS
    fft             Returns signal waveform and FFT so it can be plotted.  This
                    significantly slows down the acquisition because it computes
                    the FFT.

    RETURNS         Measuring microphone sensitivity in Vrms/Pa
    '''
    signals = acquire(dev, samples, averages)
    extract = globals()['get_rms_power_' + mode]
    components = [extract(dev.fs, s, freq) for s in signals]
    vrms, phi = np.array(components).mean(0)

    if fft:
        result = fft_analyze(signals, dev.fs)
        return vrms, phi, result
    else: return vrms, phi
    
def tone_component(waveforms, frequency, mode='conv'):
    extract = globals()['get_rms_power_' + mode]
    components = [extract(dev.fs, s, freq) for s in signals]
    vrms, phi = np.array(components).mean(0)

def do_ref_cal(calibration):
    sens, fft = ref_cal(calibration.ref_duration,
                     calibration.ref_averages,
                     calibration.standard)
    calibration.microphone.actual_sens = sens
    


def ref_cal(duration=1, averages=2, standard=None):
    '''Calibrates measuring microphone against a known reference (e.g. a
    pistonphone).  Typically this is the B&K microphone, but certainly could be
    any microphone that is felt to produce a flat frequency response across the
    range of frequencies of interest.
    '''
    # Prepare equipment for recording.  Since the signal comes from the
    # known reference, we do not play anything at all.
    device = DAQ.init_device(**DAQ_SETTINGS)
    device.play_duration.value = 0
    device.rec_duration_n.set(duration, 's')
    
    # Important, rec_delay must be at least 1 or the circuit will not work (see
    # comment in circuit).
    device.rec_delay.value = 1

    # Do the calibration!
    waveforms = acquire(dev, device.rec_duration_n.value, averages)
    power = tone_power
    
    
    result = tone_power(device, samples,
                        averages=averages,
                        freq=standard.frequency,
                        fft=fft, mode=mode)

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

def tone_cal(freq, microphone, duration=.25, rec_delay=0.1, atten=10):
    if not rec_delay > 0:
        raise ValueError("Delay of recording must be greater than zero")

    # We need to initialize device so we can obtain certain parameters from it
    # (specifically the sampling frequency).
    tone = Tone(frequency=freq, fs=dev.fs, duration=play_dur, amplitude=1)
    dev = DAQ.init_device(**DAQ_SETTINGS)
    dev.play_duration_n.set(samples, 's')
    dev.rec_duration_n.set(samples, 's')
    dev.rec_delay_n.set(rec_delay, 's')
    dev.signal.set(tone.signal)


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

if __name__ == '__main__':
    #CalibrationView().configure_traits()
    Calibration().configure_traits(view=calibration_view)

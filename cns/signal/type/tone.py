from enthought.traits.api import CFloat
from ..signal import Signal
import numpy as np

class Tone(Signal):

    frequency   = CFloat(500, configurable=True, 
                         label='Frequency', unit='Hz',
                         store='attribute')

    #def _get_amplitude(self):
    #    '''Returns scaling factor needed to achieve requested level given the
    #    current PA5 attenuation.  If calibration file is none, returns 10 (the
    #    maximum value allowed by the TDT system).
    #    '''
    #    if self.calibration is not None:
    #        max_level = self.calibration.maxspl(self.frequency)-self.actual_atten
    #        db_difference = max_level-self.level
    #    else: return 10.0
    
    def get_waveform(self, attenuation, calibration):
        dB = attenuation-self.preferred_attenuation(calibration)
        amplitude = self.amplitude_sf(dB)
        return amplitude*np.sin(self.t*2*np.pi*self.frequency)
    
    def preferred_attenuation(self, calibration):
        return calibration.maxspl(self.frequency)-self.level
    
    def _get_signal(self):
        return self.amplitude*np.sin(self.t*2*np.pi*self.frequency)

    def _get_period(self):
        return self.frequency**-1

from ..signal import Signal
from enthought.traits.api import CFloat
import numpy as np

class Chirp(Signal):
    
    # TODO: The problem is that chirp cannot allow dduration to be defined!

    freq_start  = CFloat(50, configurable=True, 
                         label='Start frequency', unit='Hz',
                         store='attribute')
    freq_end    = CFloat(50e3, configurable=True, 
                         label='End frequency', unit='Hz',
                         store='attribute')
    freq_step   = CFloat(100, configurable=True, 
                         label='Step frequency', unit='Hz',
                         store='attribute')

    def _get_signal(self):
        # Generates a chirp stimulus that can be used for calculation.  Chirp is
        # calculated after Schroeder (1970), Eq. 10.  The idea for using a chirp
        # stimulus is adapted from Keith Hancock's work for the LabVIEW-driven
        # code used to run EPL's PXI chassis.
        lb = np.ceil(self.freq_start/self.freq_step)
        ub = np.ceil(self.freq_end/self.freq_step)
        magnitude = np.zeros(self.fs/self.freq_step)
        magnitude[lb:ub] = 1

        magnitude = (magnitude**2)/np.sum(magnitude)
        phase = -np.cumsum(np.cumsum(magnitude*2*np.pi))-np.pi/2.

        signal = np.real(np.fft.ifft(magnitude*np.exp(phase*1j)))
        scale = 10/np.abs(signal).max()
        return signal*scale
    
    def get_period(self):
        return None


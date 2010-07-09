'''
Created on Mar 29, 2010

@author: Brad Buran
'''

import numpy as np

class Calibration(object):
    
    def get_calibration(self, frequencies):
        magnitude = np.interp(frequencies, self.frequencies, self.magnitude, 
                              right=np.nan, left=np.nan)
        phase = np.interp(frequencies, self.frequencies, self.phase,
                              right=np.nan, left=np.nan)
        return magnitude, phase

    def get_attenuation(self, frequencies):
        pass
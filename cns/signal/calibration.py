import numpy as np

class Calibration(object):

    frequencies = None
    spl = None

    def maxspl(self, frequencies):
        return np.interp(frequencies, self.frequencies, self.spl,
                         left=np.nan, right=np.nan)

class DummyCalibration(Calibration):

    def maxspl(self, frequency):
        try: return np.ones(len(frequency))*100
        except TypeError: return 100

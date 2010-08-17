def dsp(dsp='TDT'):
    return __import__(dsp, globals=globals(), level=1)

def pump(pump='new_era'):
    return __import__(pump, globals=globals(), level=1)

def atten():
    return Attenuator()

class EquipmentError(BaseException):

    def __init__(self, device, mesg):
        self.device = device
        self.mesg = mesg

    def __str__(self):
        return '%s: %s' % (self.device, self.mesg)

class SignalManager(object):

    def __init__(self, signal, buffer):
        self.signal = signal
        self.buffer = buffer

class Attenuator(object):

    max_voltage = 10.0  # Max peak to peak voltage output of system
    max_attenuation = 120.0 # Maximum attenuation of system
    dev_id = 'PA5_1'
    signals = []
    calibration = None

    def initialize(self):
        atten = self.best_atten()
        self.set_atten(atten)
        self.iface.SetAttenuation(atten)

    def set_atten(self, atten):
        self.atten = atten
        for signal in self.signals:
            signal.atten = atten

    def best_atten(self):
        '''Given all the signals registered with the attenuator, determine what
        the maximum attenuation we can set is.'''
        return min([s.pref_atten(self.calibration) for s in self.signals])

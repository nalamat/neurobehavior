'''
Created on Jun 9, 2010

@author: admin_behavior
'''
from cns import equipment
from enthought.pyface.timer.api import Timer
import numpy as np

class TestController(object):
    
    def __init__(self):
        self.RZ5 = equipment.dsp().init_device('MedusaRecord_v4', 'RZ5')
        self.RZ5.mc_sig.initialize(channels=16, read_mode='continuous')
        self.RZ5.mc_sig16.initialize(channels=16, read_mode='continuous', src_type=np.int16, 
                                     sf=81917500, compression='decimated')
        self.timer = Timer(500, self.tick)
        self.RZ5.start()

    def tick(self):
        print 'tick'
        data = self.RZ5.mc_sig.read()
        print data.shape
        data = self.RZ5.mc_sig16.read()
        print data.shape

if __name__ == '__main__':
    import time
    t = TestController()
    time.sleep(10)

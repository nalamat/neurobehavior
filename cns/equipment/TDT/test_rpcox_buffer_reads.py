import unittest
from cns import equipment
import numpy as np 
import time

read_mode = 'continuous'
channels = 4
int8_sf = 31
int16_sf = 6553

mc_settings = {'src_type'  		: np.float32,
               'channels'  		: channels,
               'sf'         	: 1, 
               'read_mode'  	: read_mode,
               'multiple'   	: 1,
               'compression'    : None,}

mc8_settings = {'src_type'  	: np.int8,
               'channels'  		: channels,
               'sf'         	: int8_sf, 
               'read_mode'  	: read_mode,
               'multiple'   	: 1,
               'compression'    : 'decimated',}

mc16_settings = {'src_type'  	: np.int16,
               'channels'  		: channels,
               'sf'         	: int16_sf, 
               'read_mode'  	: read_mode,
               'multiple'   	: 1,
               'compression'    : 'decimated',}

sh8_settings = {'src_type'  	: np.int8,
               'channels'  		: channels,
               'sf'         	: int8_sf, 
               'read_mode'  	: read_mode,
               'multiple'   	: 1,
               'compression'    : 'shuffled',}

sh16_settings = {'src_type'  	: np.int16,
               'channels'  		: 2,
               'sf'         	: int16_sf, 
               'read_mode'  	: read_mode,
               'multiple'   	: 1,
               'compression'    : 'shuffled',}

c16_settings = {'src_type'  	: np.int16,
               'channels'  		: 1,
               'sf'         	: int16_sf, 
               'read_mode'  	: read_mode,
               'multiple'   	: 1,
               'compression'    : 'decimated',}

class TestBufferRead(unittest.TestCase):

    def setUp(self):
        self.circuit = equipment.dsp().load('test/data_reduction_RX6', 'RX6')
        self.circuit.nHi.value = 4
        self.circuit.start()
        
        self.shape = (4, 4)

        self.circuit.mc.initialize(**mc_settings)
        self.circuit.mc8.initialize(**mc8_settings)
        self.circuit.mc16.initialize(**mc16_settings)
        self.circuit.sh8.initialize(**sh8_settings)
        self.circuit.sh16.initialize(**sh16_settings)
        self.circuit.c16.initialize(**c16_settings)

        self.circuit.trigger(1)
        time.sleep(0.1)

    def tearDown(self):
        self.circuit.stop()

    def assertShape(self, data):
        self.assertEquals(data.shape, self.shape)

    def assertSeqSamples(self, data, res):
        seq_samples = np.abs(np.diff(data, axis=0)-0.1) < res
        self.assertTrue(seq_samples.all())

    def assertSeqChannels(self, data, res):
        ch_samples = np.abs(np.diff(data, axis=1)-1) < res
        self.assertTrue(ch_samples.all())

        ch = np.floor(data)-range(self.shape[-1])
        self.assertTrue(ch.sum() == 0)

    def assertValid(self, buffer):
        buffer = getattr(self.circuit, buffer)
        data = buffer.read()
        res = buffer.resolution()
        
        self.assertShape(data)
        self.assertSeqSamples(data, res)
        if data.ndim > 1:
            self.assertSeqChannels(data, res)

    def test_mc(self): 
        self.assertValid('mc')

    def test_mc8(self):
        self.assertValid('mc8')

    def test_mc16(self):
        print 'mc16'
        self.assertValid('mc16')

    def test_sh8(self):
        print 'sh8'
        self.assertValid('sh8')

    def test_sh16(self):
        print 'sh16'
        self.shape = (4, 2)
        self.assertValid('sh16')

    def test_c16(self):
        print 'c16'
        self.shape = (4,)
        self.assertValid('c16')

    def test_mc_2(self):
        self.assertValid('mc')
        self.circuit.trigger(1)
        time.sleep(0.1)
        self.assertValid('mc')

    def test_mc16_2(self):
        self.assertValid('mc16')
        self.circuit.trigger(1)
        time.sleep(0.1)
        self.assertValid('mc16')

if __name__ == '__main__':
    unittest.main() 

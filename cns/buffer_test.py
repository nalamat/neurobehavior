import unittest
import numpy as np
from numpy.testing import assert_array_equal

from cns import buffer

class TestRingBuffer(unittest.TestCase):

    def setUp(self):
        self.size = np.random.randint(100, 1000)
        self.data = np.random.randn(self.size*4)
        #self.data = np.arange(self.size*4)
        self.buffer = buffer.SoftwareRingBuffer(self.size)

    def testLargeWrite(self):
        size = int(self.size*1.5)
        written = self.buffer.write(self.data[:size])
        self.assertEqual(written, self.size)
        assert_array_equal(self.buffer.data, self.data[size-self.size:size])

    def testSmallWrite(self):
        size = int(self.size*.5)
        written = self.buffer.write(self.data[:size])
        self.assertEqual(written, size)
        assert_array_equal(self.buffer.data[-size:], self.data[:size])
        assert_array_equal(self.buffer.data[:-size].sum(), 0) 

    def testRingWrite(self):
        size = int(self.size*.75)
        written = self.buffer.write(self.data[:size])
        written += self.buffer.write(self.data[size:size*2])
        written += self.buffer.write(self.data[size*2:size*3])
        self.assertEqual(written, size*3)
        assert_array_equal(self.buffer.data, self.data[size*3-self.size:size*3])

class Test2DRingBuffer(unittest.TestCase):

    def setUp(self):
        self.samples = np.random.randint(100, 1000)
        self.channels = np.random.randint(100, 1000)

        #self.data = np.random.randn(self.size*4)
        #self.data = np.arange(self.size*4)
        self.buffer = buffer.SoftwareRingBuffer((self.samples, self.channels))

    def test1DWrite(self):
        data = np.arange(self.channels)
        self.buffer.write(data)

        expected = np.zeros((self.samples, self.channels))
        expected[-1] = data
        assert_array_equal(self.buffer.data, expected)
        data.shape = (1, self.channels)
        assert_array_equal(self.buffer.buffered, data)

if __name__ == '__main__':
    unittest.main()

'''
Created on Jul 20, 2010

@author: Brad
'''
import unittest
import tables
import numpy as np
from cns import channel

class Test(unittest.TestCase):


    def setUp(self):
        self.file = tables.openFile('test_channel.h5', 'w')
        self.channel = channel.FileChannel(node=self.file.root,
                                           dtype=np.int16)

    def tearDown(self):
        pass


    def testName(self):
        self.assertEqual(self.channel.buffer.atom, tables.Int16Atom())

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
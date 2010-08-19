'''
Created on May 11, 2010

@author: admin_behavior
'''

from .aversive_data import AversiveData
from cns.channel import FileMultiChannel, FileChannel
from enthought.traits.api import Instance, Range
import numpy as np

class AversivePhysiologyData(AversiveData):
    
    neural_data = Instance(FileMultiChannel, store='automatic')
    neural_triggers = Instance(FileChannel, store='automatic')
    ch_monitor = Range(1, 16, 1)
    
    def _neural_data_default(self):
        return FileMultiChannel(node=self.store_node, name='neural', type=np.float32,
                                channels=17, window_fill=0)
    def _neural_triggers_default(self):
        return FileChannel(node=self.store_node, name='neural_triggers', type=np.float32, 
                           window_fill=0)
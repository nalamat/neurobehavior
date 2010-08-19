'''
Created on May 10, 2010

@author: Brad
'''

from .aversive_controller import AversiveController
from cns import equipment
from cns.data.h5_utils import append_node
from cns.experiment.data.aversive_physiology_data import AversivePhysiologyData
from enthought.traits.api import Any, on_trait_change, Range, Instance
from datetime import datetime
import numpy as np
from cns.widgets.views.channel_view import MultiChannelView

class AversivePhysiologyController(AversiveController):

    circuit_physiology = Any
    ch_monitor = Range(1, 16, 1)
    
    def init_equipment(self, info):
        super(AversivePhysiologyController, self).init_equipment(info)
        self.circuit_physiology = equipment.dsp().load('aversive-physiology', 'RZ5')
        self.circuit_physiology.open('mc_sig', 'r', 
                                     src_type=np.float32, 
                                     dest_type=np.float32, 
                                     channels=17, 
                                     read='continuous',
                                     sf=1)
        self.circuit_physiology.open('triggers', 'r')
        self.circuit_physiology.start()
        
    @on_trait_change('fast_tick')
    def task_update_physiology(self):
        try:
            data = self.circuit_physiology.mc_sig.next()
            self.model.data.neural_data.send(data)
            data = self.circuit_physiology.triggers.next()
            self.model.data.neural_triggers.send(data)
        except StopIteration:
            pass

    def initialize_data(self, model):
        exp_name = 'date_' + datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
        model.exp_node = append_node(model.store_node, exp_name)
        model.data_node = append_node(model.exp_node, 'AversiveData')
        model.data = AversivePhysiologyData(contact_fs=model.paradigm.actual_lick_fs,
                                  store_node=model.data_node)
        
    def _ch_monitor_changed(self, new):
        self.circuit_physiology.ch_monitor = new

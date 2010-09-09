'''
Created on May 12, 2010

@author: admin_behavior
'''

from .aversive_experiment import AversiveExperiment
from cns.experiment.controller.aversive_physiology_controller import \
    AversivePhysiologyController
from enthought.traits.api import Instance
from enthought.traits.ui.api import View
from cns.experiment.data.aversive_physiology_data import AversivePhysiologyData

class AversivePhysiologyExperiment(AversiveExperiment):
    
    data = Instance(AversivePhysiologyData, ())
    
    def _data_default(self):
        return AversivePhysiologyData(store_node=self.store_node)
    
    def traits_view(self, parent=None):
        return View(self._get_view_group(), resizable=True, kind='live', 
                    handler=AversivePhysiologyController)
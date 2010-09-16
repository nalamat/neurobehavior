#from cns.experiment.aversive_experiment import AversiveExperiment
from enthought.traits.ui.api import View

class AversiveFMExperiment(AversiveExperiment):
    
    def traits_view(self, parent=None):
        return View(self._get_view_group(), resizable=True, kind='live', 
                    handler=AversiveControllerFM)

from .aversive_experiment import AversiveExperiment
from ..controller.aversive_controller_FM import AversiveControllerFM
from enthought.traits.ui.api import View

class AversiveExperimentFM(AversiveExperiment):
    
    def traits_view(self, parent=None):
        return View(self._get_view_group(), resizable=True, kind='live', 
                    handler=AversiveControllerFM)

from enthought.traits.api import HasTraits, Any, Instance, DelegatesTo, Int
from enthought.traits.ui.api import View, Item, VGroup, HGroup, InstanceEditor

from cns.experiment.data.aversive_data import AversiveData
from cns.experiment.data.aversive_data_view import AnalyzedAversiveDataView

from cns.experiment.paradigm.aversive_paradigm import (AversiveParadigm,
                                                       AversiveFMParadigm)
from cns.experiment.controller.aversive_controller import (AversiveController,
                                                           AversiveFMController)

class AversiveExperiment(HasTraits):

    # The store node should be a reference to an animal
    animal = Any
    store_node = Any
    trial_blocks = Int(0)
    
    # Show the analyzed data
    data = Instance(AversiveData)

    analyzed = DelegatesTo('analyzed_view')
    analyzed_view = Instance(AnalyzedAversiveDataView)
    paradigm = Instance(AversiveParadigm, ())

    def _data_changed(self):
        self.analyzed_view = AnalyzedAversiveDataView(data=self.data)
    
    def _get_view_group(self):
        return HGroup(VGroup('handler.toolbar@',
                              [['animal{}~',
                               'handler.status{}~',],
                               'handler.time_elapsed{Time}~',
                               'handler.water_infused{Water infused}~',
                               '|[Experiment status]'],
                              Item('handler.pump@', editor=InstanceEditor()),
                              Item('paradigm@', editor=InstanceEditor(view='edit_view'),
                                   visible_when='handler.state=="halted"'),
                              Item('paradigm@', editor=InstanceEditor(view='run_view'),
                                   visible_when='handler.state<>"halted"'),
                              show_labels=False,
                              ),
                       Item('analyzed_view', style='custom', width=1300, height=900),
                       show_labels=False,
                       )
    
    def traits_view(self, parent=None):
        return View(self._get_view_group(), resizable=True, kind='live', 
                    handler=AversiveController)

class AversiveFMExperiment(AversiveExperiment):

    paradigm = Instance(AversiveFMParadigm, ())

    def traits_view(self, parent=None):
        return View(self._get_view_group(), resizable=True, kind='live', 
                    handler=AversiveFMController)

if __name__ == "__main__":
    import tables
    store = tables.openFile('test.h5', 'w')
    ae = AversiveFMExperiment(store_node=store.root)
    ae.configure_traits()

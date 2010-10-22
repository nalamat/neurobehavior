from enthought.traits.api import HasTraits, Any, Instance, DelegatesTo, Int
from enthought.traits.ui.api import View, Item, VGroup, HGroup, InstanceEditor

from cns.experiment.data.aversive_data import RawAversiveData as AversiveData
from cns.experiment.data.aversive_data_view import AnalyzedAversiveDataView

from cns.experiment.paradigm.aversive_paradigm import (AversiveParadigm,
                                                       AversiveFMParadigm)
from cns.experiment.controller.aversive_controller import (AversiveController,
                                                           AversiveFMController)

class AversiveExperiment(HasTraits):

    # The store node should be a reference to an animal
    animal = Any
    store_node = Any
    #trial_blocks = Int(0)
    
    # Show the analyzed data
    data = Instance(AversiveData)

    analyzed = DelegatesTo('analyzed_view')
    analyzed_view = Instance(AnalyzedAversiveDataView)
    paradigm = Instance(AversiveParadigm, ())

    def _data_changed(self, new):
        self.analyzed_view = AnalyzedAversiveDataView(data=self.analyzed)

    traits_group = HGroup(
            VGroup(
                Item('handler.toolbar', style='custom'),
                VGroup(
                    Item('animal', show_label=False),
                    Item('handler.status', show_label=False),
                    Item('handler.time_elasped'),
                    Item('handler.water_infused'),
                    label='Experiment Status',
                    style='readonly',
                    show_border=True,
                    ),
                Item('handler.pump', editor=InstanceEditor(),
                     style='custom'),
                Item('paradigm', editor=InstanceEditor(view='edit_view'),
                     style='custom',
                     visible_when='handler.state=="halted"'),
                Item('paradigm', editor=InstanceEditor(view='run_view'),
                     style='custom',
                     visible_when='handler.state<>"halted"'),
                show_labels=False,
                ),
           Item('analyzed_view',
                editor=InstanceEditor(view='test_view'),
                style='custom', width=1300, height=900),
           show_labels=False,
           )
    
    traits_view = View(traits_group,
                       resizable=True,
                       kind='live',
                       handler=AversiveController)

from enthought.traits.ui.api import Include
class AversiveFMExperiment(AversiveExperiment):

    paradigm = Instance(AversiveFMParadigm, ())

    traits_view = View(Include('traits_group'),
                       resizable=True,
                       kind='live',
                       handler=AversiveFMController)

if __name__ == "__main__":
    import tables
    store = tables.openFile('test.h5', 'w')
    ae = AversiveFMExperiment(store_node=store.root)
    ae.configure_traits()

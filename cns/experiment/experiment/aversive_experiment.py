from enthought.traits.api import HasTraits, Any, Instance, DelegatesTo, Int
from enthought.traits.ui.api import View, Item, VGroup, HGroup, \
        InstanceEditor, Include

from cns.experiment.data.aversive_data import RawAversiveData as AversiveData
from cns.experiment.data.aversive_data import AnalyzedAversiveData
from cns.experiment.data.aversive_data_view import AnalyzedAversiveDataView

from cns.experiment.paradigm.aversive_paradigm import (AversiveParadigm,
                                                       AversiveFMParadigm)
from cns.experiment.controller.aversive_controller import (AversiveController,
                                                           AversiveFMController)

class AversiveExperiment(HasTraits):

    # The store node should be a reference to an animal
    animal = Any
    store_node = Any

    data = Instance(AversiveData, ())
    analyzed = Instance(AnalyzedAversiveData)
    analyzed_view = Instance(AnalyzedAversiveDataView)

    #def _data_default(self):
    #    return AversiveData(store_node=self.store_node)

    #def _analyzed_default(self):
    #    return AnalyzedAversiveData(data=self.data)

    #def _analyzed_view_default(self):
    #    a = AnalyzedAversiveDataView(analyzed=self.analyzed)

    #analyzed_view = Instance(AnalyzedAversiveDataView, ())
    #analyzed = DelegatesTo('analyzed_view')
    #data = DelegatesTo('analyzed_view')
    
    # Show the analyzed data
    #data = Instance(AversiveData)
    #analyzed = 

    #analyzed = DelegatesTo('analyzed_view')
    #analyzed_view = Instance(AnalyzedAversiveDataView)
    paradigm = Instance(AversiveParadigm, ())

    def _data_changed(self, new):
        self.analyzed = AnalyzedAversiveData(data=self.data)
        self.analyzed_view = AnalyzedAversiveDataView(analyzed=self.analyzed)

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
                editor=InstanceEditor(),
                style='custom', width=1300, height=900),
           show_labels=False,
           )
    
    traits_view = View(traits_group,
                       resizable=True,
                       kind='live',
                       handler=AversiveController)

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

from enthought.traits.api import HasTraits, Any, Instance, DelegatesTo
from enthought.traits.ui.api import View, Item, VGroup, HGroup, InstanceEditor

from cns.experiment.data import AversiveData, AnalyzedAversiveDataView
from cns.experiment.paradigm import AversiveParadigm 
from cns.experiment.controller import AversiveController

class AversiveExperiment(HasTraits):

    # The store node should be a reference to an animal
    store_node = Any
    
    # Show the analyzed data
    data = Instance(AversiveData, ())

    analyzed = DelegatesTo('analyzed_view')
    analyzed_view = Instance(AnalyzedAversiveDataView)
    paradigm = Instance(AversiveParadigm, ())
    
    def _data_default(self):
        return AversiveData(store_node=self.store_node)

    def _data_changed(self):
        self.analyzed_view = AnalyzedAversiveDataView(data=self.data)
    
    def _get_view_group(self):
        return HGroup(VGroup('handler.toolbar@',
                              ['^handler.status{}~',
                               '^handler.time_elapsed{}~',
                               'handler.ch_monitor',
                               '|[Equipment status]'],
                              Item('handler.pump@', editor=InstanceEditor()),
                              Item('paradigm@', editor=InstanceEditor(view='edit_view'),
                                   visible_when='handler.state=="halted"'),
                              Item('paradigm@', editor=InstanceEditor(view='run_view'),
                                   visible_when='handler.state<>"halted"'),
                              show_labels=False,
                              ),
                              #Item('object.data.ch_monitor'),
                       Item('analyzed_view', style='custom', width=900, height=800),
                       show_labels=False,
                       )
    
    def traits_view(self, parent=None):
        return View(self._get_view_group(), resizable=True, kind='live', 
                    handler=AversiveController)

from enthought.traits.api import HasTraits, Any, Instance, DelegatesTo, Int
from enthought.traits.ui.api import View, Item, VGroup, HGroup, InstanceEditor

from cns.experiment.data.positive_data import PositiveData
from cns.experiment.paradigm.positive_paradigm import PositiveParadigm
from cns.experiment.controller.positive_controller import PositiveController

class PositiveExperiment(HasTraits):

    # The store node should be a reference to an animal
    animal = Any
    store_node = Any
    data = Instance(PositiveData, ())
    paradigm = Instance(PositiveParadigm, ())
    
    def _data_default(self):
        return PositiveData(store_node=self.store_node)

    def _get_view_group(self):
        return HGroup(VGroup('handler.toolbar@',
                              [['animal{}~',
                               'handler.status{}~',],
                               'handler.time_elapsed{Time}~',
                               'handler.water_infused{Water infused}~',
                               '|[Experiment status]'],
                              #Item('handler.pump@', editor=InstanceEditor()),
                              Item('paradigm@', editor=InstanceEditor(view='edit_view')),
                              show_labels=False,
                              ),
                       Item('analyzed_view', style='custom', width=1300, height=900),
                       show_labels=False,
                       )
    
    def traits_view(self, parent=None):
        return View(self._get_view_group(), resizable=True, kind='live', 
                    handler=PositiveController)

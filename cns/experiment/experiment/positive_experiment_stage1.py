from enthought.traits.api import HasTraits, Any, Instance, DelegatesTo, Int
from enthought.traits.ui.api import View, Item, VGroup, HGroup, InstanceEditor

from cns.experiment.data.positive_data import PositiveData
from cns.experiment.controller.positive_controller_stage1 import \
    PositiveController

from cns.widgets.views.channel_view import MultipleChannelView, MultiChannelView

class PositiveExperiment(HasTraits):

    # The store node should be a reference to an animal
    animal = Any
    store_node = Any
    data = Instance(PositiveData, ())

    contact_plot = Instance(MultipleChannelView)

    def _contact_plot_default(self):
        view = MultipleChannelView(value_title='Contact Fraction',
                value_min=0,
                value_max=1,
                interactive=False,
                window=5,
                clean_data=True,)
        view.add(self.data.optical_digital,
                 decimate_mode='mean', color='black', line_width=3)
        return view
    
    def _data_default(self):
        return PositiveData(store_node=self.store_node)

    def _get_view_group(self):
        return HGroup(VGroup('handler.toolbar@',
                             'handler.attenuation',
                              [['animal{}~',
                               'handler.status{}~',],
                               'handler.time_elapsed{Time}~',
                               'handler.water_infused{Water infused}~',
                               '|[Experiment status]'],
                              Item('handler.pump@', editor=InstanceEditor()),
                              show_labels=False,
                              ),
                       Item('contact_plot', style='custom', width=600,
                           height=600),
                       show_labels=False,
                       )
    
    def traits_view(self, parent=None):
        return View(self._get_view_group(), resizable=True, kind='live', 
                    handler=PositiveController)

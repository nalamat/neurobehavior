from enthought.traits.api import HasTraits, Any, Instance, DelegatesTo, Int
from enthought.traits.ui.api import View, Item, VGroup, HGroup, InstanceEditor

from cns.experiment.data.positive_data import PositiveData
from cns.experiment.paradigm.positive_paradigm import PositiveParadigm
from cns.experiment.controller.positive_controller import PositiveController

from cns.widgets.views.channel_view import MultipleChannelView, \
        MultiChannelView, TTLChannelView

class PositiveExperiment(HasTraits):

    # The store node should be a reference to an animal
    animal = Any
    store_node = Any
    data = Instance(PositiveData, ())
    paradigm = Instance(PositiveParadigm, ())

    contact_plot = Instance(TTLChannelView)

    def log_event(self, ts, name, value):
        pass

    def _contact_plot_default(self):
        view = TTLChannelView(
                value_title='Contact Fraction',
                value_min=0,
                value_max=1,
                interactive=False,
                window=5,
                clean_data=True,)

        view.add(self.data.poke_TTL, label='Nose Poke',
                 decimate_mode='mean', color='black', line_width=2)
        #view.add(self.data.trial_TTL, label='Trial Running',
                 #decimate_mode='mean', color='red', line_width=2)
        view.add(self.data.signal_TTL, label='Signal Playing',
                 decimate_mode='mean', color='yellow', line_width=2)
        view.add(self.data.response_TTL, label='Response Window',
                 decimate_mode='mean', color='purple', line_width=2)
        view.add(self.data.score_TTL, label='Score Window',
                 decimate_mode='mean', color='green', line_width=2)
        view.add(self.data.reward_TTL, label='Reward Window',
                 decimate_mode='mean', color='brown', line_width=2)
        view.add(self.data.spout_TTL, label='Spout Contact',
                 decimate_mode='mean', color='orange', line_width=2)
        view.add(self.data.pump_TTL, label='Pump Running',
                 decimate_mode='mean', color='blue', line_width=2)
        return view
    
    def _data_default(self):
        return PositiveData(store_node=self.store_node)

    def _get_view_group(self):
        return HGroup(VGroup('handler.toolbar@',
                              [['animal{}~',
                               'handler.status{}~',],
                               'handler.time_elapsed{Time}~',
                               'handler.water_infused{Water infused}~',
                               '|[Experiment status]'],
                              Item('handler.pump@', editor=InstanceEditor()),
                              Item('paradigm@', editor=InstanceEditor(view='edit_view')),
                              show_labels=False,
                              ),
                       Item('contact_plot', style='custom', width=600,
                           height=600),
                       show_labels=False,
                       )
    
    def traits_view(self, parent=None):
        return View(self._get_view_group(), resizable=True, kind='live', 
                    handler=PositiveController)

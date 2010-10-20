from enthought.traits.api import HasTraits, Any, Instance, DelegatesTo, Int
from enthought.traits.ui.api import View, Item, VGroup, HGroup, InstanceEditor,\
    VSplit, HSplit, TabularEditor, Group

from cns.experiment.data.positive_data import PositiveData
from cns.experiment.paradigm.positive_paradigm import PositiveParadigm
from cns.experiment.controller.positive_controller import PositiveController

from cns.widgets.views.channel_view import MultipleChannelView, \
        MultiChannelView, TTLChannelView

from enthought.traits.ui.tabular_adapter import TabularAdapter

colors = {'light green': '#98FB98',
          'dark green': '#2E8B57',
          'light red': '#FFC8CB',
          'dark red': '#FA8072', }

#class ActionLogAdapter(TabularAdapter):
#    """
#    Adapt action log to a table view
#    """
#
#    columns = ('ts', 'action')
#
#    colormap = {'TRIAL_SPOUT': '#ADD8E6',
#                'TRIAL_POKE': '#FFB6C1',
#                'NONTRIAL_POKE_WD': '#D3D3D3',
#                'NONTRIAL_SPOUT' : '#D3F3F3',
#                }
#
#    def _get_bg_color(self):
#        return self.colormap[self.item[1]]

class TrialLogAdapter(TabularAdapter):
    """
    Adapt trial log to a table view
    """

    columns = ('start', 'end', 'type', 'response')


    def _get_bg_color(self):
        if self.item[-1] in ['NO_WITHDRAW', 'NO_RESPONSE']:
            return '#D3D3D3'
        elif self.item[2] == 'GO':
            if self.item[3] == 'SPOUT': #HIT
                return colors['dark green']
            else: #MISS
                return colors['light green']
        else:
            if self.item[3] == 'SPOUT': #FA
                return colors['dark red']
            else: #CR
                return colors['light red']

#action_log_table = TabularEditor(adapter=ActionLogAdapter(),
#                                 editable=False)
trial_log_table = TabularEditor(adapter=TrialLogAdapter(),
                                editable=False)

class PositiveExperiment(HasTraits):

    # The store node should be a reference to an animal
    animal = Any
    store_node = Any
    exp_node = Any

    data = Instance(PositiveData, ())
    paradigm = Instance(PositiveParadigm, ())

    contact_plot = Instance(TTLChannelView)

    def log_event(self, ts, name, value):
        pass

    def _data_changed(self):
        view = TTLChannelView(
                value_title='Contact Fraction',
                value_min=0,
                value_max=1,
                interactive=False,
                window=.5,
                clean_data=True,)

        lw = 4
        view.add(self.data.poke_TTL, label='Nose Poke',
                 decimate_mode='mean', color='black', line_width=lw)
        #view.add(self.data.trial_TTL, label='Trial Running',
        #         decimate_mode='mean', color='red', line_width=lw)
        view.add(self.data.signal_TTL, label='Signal Playing',
                 decimate_mode='mean', color='yellow', line_width=lw)
        view.add(self.data.response_TTL, label='Response Window',
                 decimate_mode='mean', color='purple', line_width=lw)
        view.add(self.data.score_TTL, label='Score Window',
                 decimate_mode='mean', color='green', line_width=lw)
        view.add(self.data.reward_TTL, label='Reward Window',
                 decimate_mode='mean', color='brown', line_width=lw)
        view.add(self.data.spout_TTL, label='Spout Contact',
                 decimate_mode='mean', color='orange', line_width=lw)
        #view.add(self.data.pump_TTL, label='Pump Running',
        #         decimate_mode='mean', color='blue', line_width=lw)
        self.contact_plot = view

    #def _contact_plot_default(self):
    #    view = TTLChannelView(
    #            value_title='Contact Fraction',
    #            value_min=0,
    #            value_max=1,
    #            interactive=False,
    #            window=.5,
    #            clean_data=True,)

    #    view.add(self.data.poke_TTL, label='Nose Poke',
    #             decimate_mode='mean', color='black', line_width=2)
    #    view.add(self.data.trial_TTL, label='Trial Running',
    #             decimate_mode='mean', color='red', line_width=2)
    #    view.add(self.data.signal_TTL, label='Signal Playing',
    #             decimate_mode='mean', color='yellow', line_width=2)
    #    view.add(self.data.response_TTL, label='Response Window',
    #             decimate_mode='mean', color='purple', line_width=2)
    #    view.add(self.data.score_TTL, label='Score Window',
    #             decimate_mode='mean', color='green', line_width=2)
    #    view.add(self.data.reward_TTL, label='Reward Window',
    #             decimate_mode='mean', color='brown', line_width=2)
    #    view.add(self.data.spout_TTL, label='Spout Contact',
    #             decimate_mode='mean', color='orange', line_width=2)
    #    view.add(self.data.pump_TTL, label='Pump Running',
    #             decimate_mode='mean', color='blue', line_width=2)
    #    return view

    #fa_frac = DelegatesTo('data')
    #hit_frac = DelegatesTo('data')

    #spout_nontrial_ts = DelegatesTo('data')
    #spout_poke_wd_nontrial_ts = DelegatesTo('data')
    #trial_repoke_ts = DelegatesTo('data')
    #trial_spout_ts = DelegatesTo('data')
    
    def _data_default(self):
        return PositiveData(store_node=self.store_node)

    def _get_view_group(self):
        return HSplit(
            VGroup(
                VGroup(
                    'handler.toolbar@',
                    #Group(Item('animal', show_label=False, style='readonly')),
                    Item('handler.status', style='readonly'),
                    Item('handler.current_poke_dur', label='Poke duration (s)',
                         style='readonly'),
                    #Item('handler.time_elasped', label='Time', style='readonly'),
                    #Item('handler.water_infused', style='readonly'),
                    label='Experiment Status',
                    show_labels=False,
                ),
                Item('handler.pump@', editor=InstanceEditor()),
                Item('paradigm@', editor=InstanceEditor(view='edit_view')),
                show_labels=False,
            ),
            VGroup(
                VGroup(
                    Item('object.data.num_go', label='Total GO'),
                    Item('object.data.num_go_response', 
                         label='Total GO with response'),
                    Item('object.data.num_hit', label='Total hits'),
                    Item('object.data.num_nogo', label='Total NOGO'),
                    Item('object.data.num_nogo_response', 
                         label='Total NOGO with response'),
                    Item('object.data.num_fa', label='Total FA'),
                    Item('object.data.fa_frac', label='FA fraction'),
                    Item('object.data.response_fa_frac', 
                         label='FA fraction (all)'),
                    Item('object.data.hit_frac', label='HIT fraction'),
                    Item('object.data.response_hit_frac', 
                         label='HIT fraction (all)'),
                    style='readonly',
                ),
                Item('object.data.action_log', editor=action_log_table),
                Item('object.data.trial_log', editor=trial_log_table),
                show_labels=False,
            ),
            Item('contact_plot', style='custom', width=600, height=600), 
            show_labels=False,
        )
    
    def traits_view(self, parent=None):
        return View(self._get_view_group(), resizable=True, kind='live',
                id='cns.experiment.positive_experiment',
                close_result=False,
                handler=PositiveController)

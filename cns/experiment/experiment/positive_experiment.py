from enthought.traits.api import HasTraits, Any, Instance, DelegatesTo, Int
from enthought.traits.ui.api import View, Item, VGroup, HGroup, InstanceEditor,\
    VSplit, HSplit, TabularEditor, Group

from cns.experiment.data.positive_data import PositiveData
from cns.experiment.paradigm.positive_paradigm import PositiveParadigm
from cns.experiment.controller.positive_controller import PositiveController

from cns.widgets.views.channel_view import MultipleChannelView, \
        MultiChannelView, TTLChannelView

colors = {'light green': '#98FB98',
          'dark green': '#2E8B57',
          'light red': '#FFC8CB',
          'dark red': '#FA8072',
          'gray': '#D3D3D3',
          'light blue': '#ADD8E6',
          }

from enthought.traits.ui.api import TableEditor, ListColumn

class TrialTypeColumn(ListColumn):

    def get_cell_color(self, object):
        if object[2] == 'GO':
            return colors['light green']
        else:
            return colors['light red']

class TrialResponseColumn(ListColumn):

    def get_cell_color(self, object):
        response = object[-1]
        if response in ['NO_WITHDRAW', 'NO_RESPONSE']:
            return '#FFFFFF'
        elif response == 'SPOUT':
            return colors['light blue']
        else:
            return colors['gray']

trial_log_table = TableEditor(
        editable=False,
        sortable=True,
        sort_model=False,
        columns=[
            TrialTypeColumn(index=0, label='start'),
            TrialTypeColumn(index=1, label='end'),
            TrialTypeColumn(index=2, label='type'),
            TrialResponseColumn(index=3, label='response'),
            ]
        )

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
        self.contact_plot = view

    def _data_default(self):
        return PositiveData(store_node=self.store_node)

    traits_view = View(
            HSplit(
                VGroup(
                    VGroup(
                        'handler.toolbar@',
                        Item('handler.status', style='readonly'),
                        Item('handler.current_poke_dur', 
                             label='Poke duration (s)', style='readonly'),
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
                    Item('object.data.trial_log', editor=trial_log_table),
                    show_labels=False,
                ),
                Item('contact_plot', style='custom', width=600, height=600), 
                show_labels=False,
            ),
            resizable=True,
            kind='live',
            id='cns.experiment.positive_experiment',
            close_result=False,
            handler=PositiveController)

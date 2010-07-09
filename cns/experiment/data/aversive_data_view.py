from .experiment_data_view import AnalyzedView
from cns.experiment.data import AnalyzedAversiveData
from cns.widgets.views.channel_view import MultipleChannelView, MultiChannelView
from cns.widgets.views.chart_view import DynamicBarPlotView, HistoryBarPlotView
from cns.widgets.views.component_view import BarChartOverlay
from enthought.enable.component_editor import ComponentEditor
from enthought.traits.api import Instance, DelegatesTo
from enthought.traits.ui.api import View, VGroup, HGroup, Item
from numpy import clip

PLOT_HEIGHT = 200
PLOT_WIDTH = 200

class AnalyzedAversiveDataView(AnalyzedView):

    analyzed = Instance(AnalyzedAversiveData, ())
    data = DelegatesTo('analyzed')

    par_fa_frac_chart = Instance(DynamicBarPlotView)
    par_hit_frac_chart = Instance(DynamicBarPlotView)
    par_count_chart = Instance(DynamicBarPlotView)

    score_chart = Instance(BarChartOverlay)
    contact_plot = Instance(MultipleChannelView)
    #raw_contact_plot = Instance(MultipleChannelView)
    raw_contact_plot = Instance(MultiChannelView)

    def _contact_plot_default(self):
        view = MultipleChannelView(value_title='Contact Fraction',
                value_min=0,
                value_max=1,
                interactive=False,
                window=5,
                clean_data=True,
                )
        view.add(self.analyzed.data.contact_data, 
                 decimate_mode='mean', ch_index=3, color='red', line_width=3)
        view.add(self.analyzed.data.contact_data, 
                 decimate_mode='mean', ch_index=0, color='gray')
        view.add(self.analyzed.data.contact_data, 
                 decimate_mode='mean', ch_index=1, color='black', line_width=2)
        return view

    def _raw_contact_plot_default(self):
        view = MultiChannelView(window=1, visible=[self.data.ch_monitor],
                                channel=self.data.neural_data)
        return view

        view = MultipleChannelView(
                value_title='Contact Fraction',
                value_min='auto',
                value_max='auto',
                interactive=False,
                window=5)
        return view

    def _par_count_chart_default(self):
        return DynamicBarPlotView(
                source=self.analyzed.data,
                value='par_count',
                label='pars',
                index_title='Parameter',
                value_title='Number of Trials',
                bar_color='black',
                bar_width=0.9,
                value_min=0,
                value_max=1,
                )

    def _par_hit_frac_chart_default(self):
        return DynamicBarPlotView(
                source=self.analyzed,
                label='pars',
                value='par_hit_frac',
                index_title='Parameter',
                value_title='Hit Fraction',
                bar_width=0.9,
                value_min=0,
                value_max=1,
                )

    def _par_fa_frac_chart_default(self):
        return DynamicBarPlotView(
                source=self.analyzed,
                label='pars',
                value='par_fa_frac',
                index_title='Parameter',
                value_title='FA Fraction',
                bar_width=0.9,
                value_min=0,
                value_max=1,
                )

    def _score_chart_default(self):
        template = HistoryBarPlotView(is_template=True,
                                      preprocess_values=lambda x: clip(x, 0.2, 1.0),
                                      value_min=0,
                                      value_max=1,
                                      index_title='Trial',
                                      value_title='Score',
                                      title='')
        self.analyzed.sync_trait('curidx', template, 'current_index')
        view = BarChartOverlay(template=template)
        view.add(
                source=self.analyzed,
                index='remind_indices',
                value='remind_seq',
                bar_color='lightgray',
                bar_width=1,
                title='HIT (reminder)',
                )
        view.add(
                source=self.analyzed,
                index='safe_indices',
                value='fa_seq',
                bar_color='lightpink',
                bar_width=1,
                title='FA',
                )
        view.add(
                source=self.analyzed,
                index='warn_indices',
                value='hit_seq',
                bar_color='red',
                bar_width=1,
                title='HIT',
                )
        view.add_legend()
        return view

    kw_component = dict(height=PLOT_HEIGHT, width=PLOT_WIDTH)
    kw_plot = dict(editor=ComponentEditor(**kw_component),
                        show_label=False)

    group = HGroup([#Item('object.raw_contact_plot.component', **kw_plot),
                    Item('object.contact_plot.component', **kw_plot),
                    'score_chart{}@',],
                   VGroup(Item('object.par_count_chart.component', **kw_plot),
                          Item('object.par_hit_frac_chart.component', **kw_plot),
                          Item('object.par_fa_frac_chart.component', **kw_plot),
                          ),
                   ),

    traits_view = View(group,
                       title='Analyzed Data',
                       resizable=True,
                       height=.9,
                       width=.75,
                       )

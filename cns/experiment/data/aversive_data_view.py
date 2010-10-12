from .experiment_data_view import AnalyzedView
from cns.experiment.data.aversive_data import BaseAnalyzedAversiveData
from cns.widgets.views.channel_view import MultipleChannelView, MultiChannelView
from cns.widgets.views.chart_view import DynamicBarPlotView, HistoryBarPlotView
from cns.widgets.views.component_view import BarChartOverlay
from enthought.enable.component_editor import ComponentEditor
from enthought.traits.api import Instance, DelegatesTo, Any
from enthought.traits.ui.api import View, Group, Item, Tabbed, HGroup, VGroup
from numpy import clip

PLOT_HEIGHT = 200
PLOT_WIDTH = 200

class Test(AnalyzedView):

    analyzed = Instance(BaseAnalyzedAversiveData, ())
    data = DelegatesTo('analyzed')

    par_count_chart = Instance(DynamicBarPlotView)

    def _par_count_chart_default(self):
        return DynamicBarPlotView(
                source=self.analyzed.data,
                value='par_warn_count',
                label='pars',
                index_title='Parameter',
                value_title='Number',
                title='Trials Presented',
                bar_color='black',
                bar_width=0.9,
                value_min=0,
                value_max='auto',
                )

    traits_view = View('par_count_chart{}@')

class AnalyzedAversiveDataView(AnalyzedView):

    analyzed = Instance(BaseAnalyzedAversiveData, ())

    # Parameter summaries
    par_fa_frac_chart = Instance(DynamicBarPlotView)
    par_hit_frac_chart = Instance(DynamicBarPlotView)
    par_count_chart = Instance(DynamicBarPlotView)
    par_dprime_chart = Instance(DynamicBarPlotView)

    def _par_count_chart_default(self):
        return DynamicBarPlotView(
                source=self.analyzed.data,
                value='par_count',
                label='pars',
                index_title='Parameter',
                value_title='Number',
                title='Trials Presented',
                bar_color='black',
                bar_width=0.9,
                value_min=0,
                value_max='auto',
                )

    def _par_hit_frac_chart_default(self):
        return DynamicBarPlotView(
                source=self.analyzed,
                label='pars',
                value='par_hit_frac',
                index_title='Parameter',
                value_title='Fraction',
                title='HIT Probability',
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
                value_title='Fraction',
                title='FA Fraction',
                bar_width=0.9,
                value_min=0,
                value_max=1,
                )

    def _par_dprime_chart_default(self):
        return DynamicBarPlotView(
                source=self.analyzed,
                label='pars',
                value='par_dprime',
                index_title='Parameter',
                value_title="d'",
                title='Overall Performance',
                bar_width=0.9,
                value_min=0,
                value_max=4,
                )

    kw_component = dict(height=PLOT_HEIGHT, width=PLOT_WIDTH)
    kw_plot = dict(editor=ComponentEditor(**kw_component),
                        show_label=False)

    #total_trials = DelegatesTo('data')
    #global_fa_frac = DelegatesTo('analyzed')
    #use_global_fa_frac = DelegatesTo('analyzed')

    #contact_offset = DelegatesTo('analyzed')
    #contact_dur = DelegatesTo('analyzed')
    #contact_fraction = DelegatesTo('analyzed')

    traits_view = View(
        Tabbed(
            #'par_count_chart{}@',
            'par_hit_frac_chart{}@',
            'par_fa_frac_chart{}',
            #VGroup(Group('total_trials~'),
            #       'par_count_chart{}@'),
            #      ),
            #VGroup(Group('use_global_fa_frac'),
            #       'par_dprime_chart{}@'),
            #'par_hit_frac_chart{}@',
            #VGroup(Group('global_fa_frac~'),
            #       'par_fa_frac_chart{}@'),
            id='cns.experiment.data_aversive_data_view.analyzed',
        ),
        title='Analyzed Data',
        resizable=True,
        dock='horizontal',
        id='cns.experiment.data.aversive_data_view'
    )


class TestView(AnalyzedView):

    data = Any

    score_chart = Instance(BarChartOverlay)

    def _score_chart_default(self):
        print 'called'
        template = HistoryBarPlotView(is_template=True,
                                      preprocess_values=lambda x: clip(x, 0.2, 1.0),
                                      value_min=0,
                                      value_max=1,
                                      index_title='Trial',
                                      value_title='Score',
                                      history=60,
                                      title='')
        #self.analyzed.sync_trait('total_indices', template, 'current_index',
        #                         mutual=False)
        view = BarChartOverlay(template=template)
        print 'check'
        try:
            view.add(source=self.analyzed,
                     index='remind_indices',
                     value='remind_seq',
                     bar_color='lightgray',
                     bar_width=1,
                     label='HIT (reminder)',
                     show_labels=False,
                    )
        except BaseException, e:
            print e

        view.add(source=self.analyzed,
                 index='safe_indices',
                 value='fa_seq',
                 bar_color='lightpink',
                 bar_width=1,
                 title='FA',
                 show_labels='False',
                )
        view.add(source=self.analyzed,
                 index='warn_indices',
                 value='hit_seq',
                 bar_color='red',
                 bar_width=1,
                 title='HIT',
                 show_labels='False',
                 )
        view.add_legend()
        print 'returning view'
        return view

    traits_view = View('score_chart{}@')

from .experiment_data_view import AnalyzedView
#from cns.experiment.data.aversive_data import AnalyzedAversiveData 
from cns.widgets.views.channel_view import MultipleChannelView, MultiChannelView
from cns.widgets.views.chart_view import DynamicBarPlotView, HistoryBarPlotView
from cns.widgets.views.component_view import BarChartOverlay
from enthought.enable.component_editor import ComponentEditor
from enthought.traits.api import Instance, DelegatesTo, Any
from enthought.traits.ui.api import View, Group, Item, Tabbed, HGroup, VGroup
from numpy import clip

PLOT_HEIGHT = 200
PLOT_WIDTH = 200

class SummaryAversiveDataView(AnalyzedView):

    SOURCE = 'cns.experiment.data.aversive_data.BaseAnalyzedAversiveData'
    analyzed = Instance(SOURCE)

    par_fa_frac_chart = Instance(DynamicBarPlotView)
    par_hit_frac_chart = Instance(DynamicBarPlotView)
    par_count_chart = Instance(DynamicBarPlotView)
    par_dprime_chart = Instance(DynamicBarPlotView)

    global_fa_frac = DelegatesTo('analyzed')
    use_global_fa_frac = DelegatesTo('analyzed')

    #contact_offset = DelegatesTo('analyzed')
    #contact_dur = DelegatesTo('analyzed')
    #contact_fraction = DelegatesTo('analyzed')

    warn_trial_count = DelegatesTo('analyzed')

    remind_indices = DelegatesTo('analyzed')
    safe_indices = DelegatesTo('analyzed')
    warn_indices = DelegatesTo('analyzed')
    total_indices = DelegatesTo('analyzed')
    remind_seq = DelegatesTo('analyzed')
    safe_seq = DelegatesTo('analyzed')
    warn_seq = DelegatesTo('analyzed')

    label = DelegatesTo('analyzed')

    def _par_count_chart_default(self):
        print 'getting chart'
        try:
            return DynamicBarPlotView(
                    source=self.analyzed,
                    label='pars',
                    value='par_warn_count',
                    index_title='Parameter',
                    value_title='Number',
                    title='Trials Presented',
                    bar_color='black',
                    bar_width=0.9,
                    value_min=0,
                    value_max='auto',
                    )
        except BaseException, e:
            print 'failed'
            print e
            import traceback
            traceback.print_exc()
            print 'traceback'

    def _par_hit_frac_chart_default(self):
        print 'attempting to get chart'
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
                value_min=-1,
                value_max=4,
                )

    #traits_view = View(
    #    Tabbed(
    #        'par_hit_frac_chart{}@',
    #        VGroup(Group(Item('global_fa_frac', label='Average FA fraction',
    #                          style='readonly')),
    #               'par_fa_frac_chart{}@'),
    #        VGroup(Group(Item('warn_trial_count', label='Total trials',
    #                          style='readonly')),
    #               'par_count_chart{}@'),
    #        VGroup(Group(Item('use_global_fa_frac', 
    #                          label='Use average FA fraction')),
    #               'par_dprime_chart{}@'),
    #        id='cns.experiment.data_aversive_data_view.analyzed',
    #    ),
    #    title='Analyzed Data',
    #    resizable=True,
    #    dock='horizontal',
    #    id='cns.experiment.data.aversive_data_view'
    #)
    traits_view = View(
        VGroup(
            HGroup('par_count_chart{}@', 'par_dprime_chart{}@'),
            HGroup('par_fa_frac_chart{}@', 'par_hit_frac_chart{}@'),
        ),
        resizable=True,
        )

class AnalyzedAversiveDataView(SummaryAversiveDataView):

    SOURCE = 'cns.experiment.data.aversive_data.AnalyzedAversiveData'
    analyzed = Instance(SOURCE)

    score_chart = Instance(BarChartOverlay)

    def _score_chart_default(self):
        template = HistoryBarPlotView(is_template=True,
                                      preprocess_values=lambda x: clip(x, 0.2, 1.0),
                                      value_min=0,
                                      value_max=1,
                                      index_title='Trial',
                                      value_title='Score',
                                      history=60,
                                      title='')
        self.analyzed.sync_trait('total_indices', template, 'current_index',
                                 mutual=False)
        view = BarChartOverlay(template=template)
        view.add(source=self.analyzed,
                 index='remind_indices',
                 value='remind_seq',
                 bar_color='lightgray',
                 bar_width=1,
                 label='HIT (reminder)',
                 show_labels=False,
                )

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
        return view

    test_view = View('par_count_chart{}@')

    summary_group = VGroup(
        HGroup(
            'par_hit_frac_chart{}@',
            VGroup(
                Group(
                    Item('global_fa_frac', label='Average FA fraction',
                         style='readonly')),
                Item('par_fa_frac_chart{}@'),
            ),
        ),
        HGroup(
            VGroup(
                Group(
                    Item('warn_trial_count', 
                         label='Total trials',
                         style='readonly')
                ),
                Item('par_count_chart{}@'),
            ),
            VGroup(
                Group(
                    Item('use_global_fa_frac', 
                         label='Use average FA fraction')),
                Item('par_dprime_chart{}@'),
            ),
        ),
    )

    contact_group = VGroup(
        'score_chart{}',
        'par_hit_frac_chart{}',
    )
    
    post_analysis_view = View(summary_group)

    traits_view = View(
        Tabbed(
            'score_chart{}@',
            'par_hit_frac_chart{}@',
            VGroup(Group(Item('global_fa_frac', label='Average FA fraction',
                              style='readonly')),
                   'par_fa_frac_chart{}@'),
            VGroup(Group(Item('warn_trial_count', label='Total trials',
                              style='readonly')),
                   'par_count_chart{}@'),
            VGroup(Group(Item('use_global_fa_frac', 
                              label='Use average FA fraction')),
                   'par_dprime_chart{}@'),
            id='cns.experiment.data_aversive_data_view.analyzed',
        ),
        title='Analyzed Data',
        resizable=True,
        dock='horizontal',
        id='cns.experiment.data.aversive_data_view'
    )

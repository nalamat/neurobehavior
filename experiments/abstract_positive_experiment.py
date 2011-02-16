from __future__ import division

import numpy as np
from enthought.traits.api import HasTraits, Any, Instance, DelegatesTo, \
        Int, Float, Property
from enthought.traits.ui.api import View, Item, VGroup, HGroup, InstanceEditor,\
    VSplit, HSplit, TabularEditor, Group, Include

from enthought.enable.api import Component, ComponentEditor

from abstract_experiment import AbstractExperiment
from positive_data import PositiveData
from abstract_positive_paradigm import AbstractPositiveParadigm
from abstract_positive_controller import AbstractPositiveController

from enthought.chaco.api import DataRange1D, LinearMapper, PlotAxis, PlotGrid, \
        OverlayPlotContainer

from cns.chaco.channel_data_range import ChannelDataRange
from cns.chaco.ttl_plot import TTLPlot
from cns.chaco.timeseries_plot import TimeseriesPlot
from cns.chaco.dynamic_bar_plot import DynamicBarPlot, DynamicBarplotAxis

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
        if object[3] == 'GO':
            return colors['light green']
        else:
            return colors['light red']

    def get_value(self, object):
        value = object[self.index]
        if type(value) in (list, tuple):
            # Default Python formatting for a tuple or list is a bit ugly, so
            # let's handle it ourselves.
            return ", ".join([str(e) for e in value])
        else:
            return str(value)

class TrialResponseColumn(ListColumn):

    MAP = {
         ('GO',   'spout')       : colors['light green'],
         ('GO',   'poke')        : colors['gray'],
         ('NOGO', 'spout')       : colors['gray'],
         ('NOGO', 'poke')        : colors['light red'],
         ('GO',   'no response') : '#FFFFFF',
         ('NOGO', 'no response') : '#FFFFFF',
         ('GO',   'no withdraw') : '#FFFFFF',
         ('NOGO', 'no withdraw') : '#FFFFFF', 
         }

    def get_cell_color(self, object):
        response = object[4]
        ttype = object[3]
        return self.MAP[(ttype, response)]

trial_log_table = TableEditor(
        editable=False,
        sort_model=False,
        reverse=True,
        columns=[
            TrialTypeColumn(index=1, label='start'),
            TrialTypeColumn(index=0, label='parameter'),
            TrialResponseColumn(index=4, label='response'),
            TrialTypeColumn(index=5, label='reaction time'),
            ]
        )

class AbstractPositiveExperiment(AbstractExperiment):

    data = Instance(PositiveData)
    paradigm = Instance(AbstractPositiveParadigm, ())

    trial_log_view = Property(depends_on='data.trial_log')

    def _data_node_changed(self, new):
        self.data = PositiveData(store_node=new)

    def _get_trial_log_view(self):
        trial_log = np.array(self.data.trial_log, dtype=object)
        if len(trial_log) > 0:
            trial_log[:,4] /= self.data.contact_fs
            return list(trial_log)
        else:
            return list(trial_log)

    experiment_plot = Instance(Component)
    par_count_plot  = Instance(Component)
    par_score_plot  = Instance(Component)
    par_dprime_plot = Instance(Component)
    
    def _data_changed(self):
        self._generate_experiment_plot()
        self._generate_summary_plots()

    def _generate_experiment_plot(self):
        plots = {}
        index_range = ChannelDataRange()
        index_range.sources = [self.data.spout_TTL]
        index_mapper = LinearMapper(range=index_range)

        container = OverlayPlotContainer(padding=50)

        value_range = DataRange1D(low_setting=-0, high_setting=1)
        value_mapper = LinearMapper(range=value_range)
        plot = TTLPlot(channel=self.data.spout_TTL, reference=0,
                index_mapper=index_mapper, value_mapper=value_mapper,
                fill_color=(0.25, 0.41, 0.88, 0.5), rect_center=0.25,
                rect_height=0.2)
        grid = PlotGrid(mapper=plot.index_mapper, component=plot,
                orientation='vertical', line_color='lightgray',
                line_style='dot', grid_interval=0.25)
        plot.underlays.append(grid)
        grid = PlotGrid(mapper=plot.index_mapper, component=plot,
                orientation='vertical', line_color='lightgray',
                line_style='solid', grid_interval=1)
        plot.underlays.append(grid)
        axis = PlotAxis(component=plot, title="Time (s)",
                        orientation="top", ticks_visible=True)
        plot.underlays.append(axis)
        tick_formatter = lambda s: "{0}:{1:02}".format(*divmod(int(s), 60))
        axis = PlotAxis(component=plot, orientation="bottom",
                title="Time(min:sec)",
                tick_label_formatter=tick_formatter)
        plot.underlays.append(axis)

        container.add(plot)

        plots["Spout Contact"] = plot

        plot = TTLPlot(channel=self.data.poke_TTL, reference=0,
                index_mapper=index_mapper, value_mapper=value_mapper,
                fill_color=(.17, .54, .34, 0.5), rect_center=0.75,
                rect_height=0.2)

        container.add(plot)
        plots["Nose Poke"] = plot

        plot = TTLPlot(channel=self.data.signal_TTL, reference=0,
                index_mapper=index_mapper, value_mapper=value_mapper,
                fill_color=(0, 0, 0, 0.25), line_color=(0, 0, 0, 0.75),
                line_width=1, rect_height=0.3, rect_center=0.5)
        container.add(plot)
        plots["Signal"] = plot

        plot = TTLPlot(channel=self.data.reaction_TTL, reference=0,
                index_mapper=index_mapper, value_mapper=value_mapper,
                fill_color=(1, 0, 0, 0.25), line_color=(1, 0, 0, 1),
                line_width=1, rect_height=0.1, rect_center=0.6)
        container.add(plot)
        plots["Reaction Window"] = plot

        plot = TTLPlot(channel=self.data.response_TTL, reference=0,
                index_mapper=index_mapper, value_mapper=value_mapper,
                fill_color=(0, 1, 0, 0.25), line_color=(0, 1, 0, 1),
                line_width=1, rect_height=0.1, rect_center=0.5)
        container.add(plot)
        plots["Response Window"] = plot

        plot = TTLPlot(channel=self.data.reward_TTL, reference=0,
                index_mapper=index_mapper, value_mapper=value_mapper,
                fill_color=(0, 0, 1, 0.25), line_color=(0, 0, 1, 1),
                line_width=1, rect_height=0.1, rect_center=0.4)
        container.add(plot)
        plots["Reward Window"] = plot

        plot = TimeseriesPlot(series=self.data.trial_start_timestamp,
                index_mapper=index_mapper, value_mapper=value_mapper,
                line_color='black', line_width=2, label="Start Trial")
        container.add(plot)

        plot = TimeseriesPlot(series=self.data.trial_end_timestamp,
                index_mapper=index_mapper, value_mapper=value_mapper,
                line_color='black', line_width=2, label="End Trial")
        container.add(plot)

        plot = TimeseriesPlot(series=self.data.timeout_start_timestamp,
                index_mapper=index_mapper, value_mapper=value_mapper,
                line_color='red', line_width=2, label="Start TIMEOUT")
        container.add(plot)

        plot = TimeseriesPlot(series=self.data.timeout_end_timestamp,
                index_mapper=index_mapper, value_mapper=value_mapper,
                line_color='red', line_width=2, label="End TIMEOUT")
        container.add(plot)

        self.experiment_plot = container

    def _generate_summary_plots(self):
        bounds = lambda low, high, margin, tight: (low-0.5, high+0.5)
        index_range = DataRange1D(bounds_func=bounds)
        index_mapper = LinearMapper(range=index_range)
        value_range = DataRange1D(low_setting=0, high_setting='auto')
        value_mapper = LinearMapper(range=value_range)

        plot = DynamicBarPlot(source=self.data,
                label_trait='pars', value_trait='par_go_count', bgcolor='white',
                padding=50, fill_padding=True, bar_width=0.9,
                value_mapper=value_mapper, index_mapper=index_mapper)
        index_range.add(plot.index)
        value_range.add(plot.value)
        grid = PlotGrid(mapper=plot.value_mapper, component=plot,
                orientation='horizontal', line_color='lightgray',
                line_style='dot', grid_interval=5)
        plot.underlays.append(grid)
        axis = DynamicBarplotAxis(plot, orientation='bottom',
                source=self.data, label_trait='pars')
        plot.underlays.append(axis)
        plot.underlays.append(PlotAxis(plot, orientation='left'))
        self.par_count_plot = plot

        # FA and HIT
        bounds = lambda low, high, margin, tight: (low-0.8, high+0.8)
        index_range = DataRange1D(bounds_func=bounds)
        index_mapper = LinearMapper(range=index_range)
        value_range = DataRange1D(low_setting=0, high_setting=1)
        value_mapper = LinearMapper(range=value_range)

        self.par_score_plot = OverlayPlotContainer(bgcolor='white',
                fill_padding=True)

        plot = DynamicBarPlot(source=self.data, label_trait='pars',
                value_trait='par_hit_frac', bgcolor='white', padding=50,
                fill_padding=True, bar_width=0.5, index_mapper=index_mapper,
                value_mapper=value_mapper, index_offset=-0.2, alpha=0.5)
        index_range.add(plot.index)

        axis = DynamicBarplotAxis(plot, orientation='bottom',
                source=self.data, label_trait='pars')
        plot.underlays.append(axis)
        plot.underlays.append(PlotAxis(plot, orientation='left'))
        
        grid = PlotGrid(mapper=plot.value_mapper, component=plot,
                orientation='horizontal', line_color='lightgray',
                line_style='dot', grid_interval=0.2)
        plot.underlays.append(grid)
        self.par_score_plot.add(plot)

        plot = DynamicBarPlot(source=self.data, label_trait='pars',
                value_trait='par_fa_frac', bgcolor='white', padding=50,
                fill_padding=True, bar_width=0.5, fill_color=(1, 0, 0),
                index_mapper=index_mapper, value_mapper=value_mapper,
                index_offset=0.2, alpha=0.5)
        index_range.add(plot.index)

        self.par_score_plot.add(plot)

        # DPRIME
        bounds = lambda low, high, margin, tight: (low-0.5, high+0.5)
        index_range = DataRange1D(bounds_func=bounds)
        index_mapper = LinearMapper(range=index_range)
        value_range = DataRange1D(low_setting=-1, high_setting=4)
        value_mapper = LinearMapper(range=value_range)

        plot = DynamicBarPlot(source=self.data,
                label_trait='pars', value_trait='par_dprime', bgcolor='white',
                padding=50, fill_padding=True, bar_width=0.9,
                value_mapper=value_mapper, index_mapper=index_mapper)
        index_range.add(plot.index)
        grid = PlotGrid(mapper=plot.value_mapper, component=plot,
                orientation='horizontal', line_color='lightgray',
                line_style='dot', grid_interval=1)
        plot.underlays.append(grid)
        axis = DynamicBarplotAxis(plot, orientation='bottom',
                source=self.data, label_trait='pars')
        plot.underlays.append(axis)
        plot.underlays.append(PlotAxis(plot, orientation='left'))
        self.par_dprime_plot = plot


    status_group = VGroup(
            Item('handler.status', style='readonly'),
            Item('handler.current_poke_dur', 
                 label='Poke duration (s)', style='readonly'),
            Item('handler.current_setting_go', style='readonly',
                 label='Current GO'),
            label='Experiment',
            show_border=True,
            )

    plots_group = VGroup(
            Item('experiment_plot', editor=ComponentEditor(),
                show_label=False, width=600, height=200),
            HGroup(
                Item('par_count_plot', editor=ComponentEditor(),
                    show_label=False, width=150, height=150),
                Item('par_score_plot', editor=ComponentEditor(),
                    show_label=False, width=150, height=150),
                Item('par_dprime_plot', editor=ComponentEditor(),
                    show_label=False, width=150, height=150)
                ),
            )

    experiment_group = VGroup(
            VGroup(
                Item('object.data.go_trial_count',
                     label='Number of GO trials'),
                Item('object.data.nogo_trial_count',
                     label='Number of NOGO trials'),
                Item('object.data.global_fa_frac',
                     label='Global FA fraction'),
                label='Experiment summary',
                show_border=True,
                style='readonly',
                ),
            Item('object.data.trial_log', editor=trial_log_table),
            show_labels=False,
            )

    traits_group = HSplit(
            VGroup(
                Item('handler.toolbar', style='custom'),
                Include('status_group'),
                Item('paradigm', style='custom', editor=InstanceEditor()),
                show_labels=False,
            ),
            Include('plots_group'),
            Include('experiment_group'),
            show_labels=False,
        )
    
    traits_view = View(
            HSplit(
                VGroup(
                    Item('handler.toolbar', style='custom'),
                    Include('status_group'),
                    Item('paradigm', style='custom', editor=InstanceEditor()),
                    show_labels=False,
                ),
                Include('plots_group'),
                Include('experiment_group'),
                show_labels=False,
                ),
            resizable=True,
            kind='live',
            handler=AbstractPositiveController)

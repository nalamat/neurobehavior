from __future__ import division

import numpy as np
from enthought.traits.api import HasTraits, Any, Instance, DelegatesTo, \
        Int, Float, Property, on_trait_change, cached_property
from enthought.traits.ui.api import View, Item, VGroup, HGroup, InstanceEditor,\
    VSplit, HSplit, TabularEditor, Group, Include, Tabbed

from enthought.enable.api import Component, ComponentEditor

import cns

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
from cns.chaco.helpers import add_default_grids, add_time_axis

from enthought.traits.ui.api import VGroup, Item

colors = {'light green': '#98FB98',
          'dark green': '#2E8B57',
          'light red': '#FFC8CB',
          'dark red': '#FA8072',
          'gray': '#D3D3D3',
          'light blue': '#ADD8E6',
          }

from enthought.traits.ui.api import TabularEditor
from enthought.traits.ui.tabular_adapter import TabularAdapter

from enthought.traits.api import *

class ParInfoAdapter(TabularAdapter):

    mean_std_fmt = u"{:.2} \u00B1 {:.2}"

    columns = [ ('Par', 'par'),
                ('Hit %', 'hit_frac'), 
                ('FA %', 'fa_frac'),
                ('d', 'd'),
                ('Reaction (s)', 'reaction'),
                ('Response (s)', 'response'),
                ]

    width = Float(50)
    reaction_width = Float(75)
    response_width = Float(75)

    reaction_text = Property
    response_text = Property

    def _get_reaction_text(self):
        return self.mean_std_fmt.format(self.item['mean_react'],
                self.item['std_react'])

    def _get_response_text(self):
        return self.mean_std_fmt.format(self.item['mean_resp'],
                self.item['std_resp'])

    def _get_bg_color(self):
        if self.item['d'] < 1:
            return colors['light red']
        else:
            return colors['light green']

par_info_editor = TabularEditor(editable=False, adapter=ParInfoAdapter())

class TrialLogAdapter(TabularAdapter):

    # List of tuples (column_name, field )
    columns = [ ('Start', 'start'),
                ('', 'early_response'),
                ('Response', 'response'), 
                ('Reaction time', 'reaction_time'),
                ('Response time', 'response_time')
                ]

    early_response_width = Float(20)
    start_width = Float(50)
    response_width = Float(100)
    reaction_time_width = Float(75)
    response_time_width = Float(75)
    response_image = Property
    early_response_image = Property

    def _get_bg_color(self):
        if self.item['ttype'] == 'GO':
            return colors['light green']
        else:
            return colors['light red']

    def _get_early_response_image(self):
        if self.item['early_response']:
            return '@icons:array_node'
        else:
            return '@icons:tuple_node'

    def _get_response_image(self):
        # Note that these are references to some icons included in ETS
        # (Enthought Tool Suite).  The icons can be found in
        # enthought/traits/ui/image/library/icons.zip under site-packages.  I
        # hand-picked a few that seemed to work for our purposes (mainly based
        # on the colors).  I wanted a spout response to have a green icon
        # associated with it (so that green on green means HIT, red on green
        # means MISS), etc.
        if self.item['response'] == 'spout':
            return '@icons:tuple_node'  # a green icon
        elif self.item['response'] == 'poke':
            return '@icons:dict_node'   # a red icon
        else:
            return '@icons:none_node'   # a gray icon

trial_log_editor = TabularEditor(editable=False, adapter=TrialLogAdapter())

class AbstractPositiveExperiment(AbstractExperiment):

    trial_log_view = Property(depends_on='data.trial_log',
            editor=trial_log_editor)

    @cached_property
    def _get_trial_log_view(self):
        # Allows us to ensure that last trial always appears at the top of
        # the list (otherwise we constantly need to scroll down to see the
        # latest trial).  Eventually we can add per-column sorting back in, but
        # that is a very low priority.
        return self.data.trial_log[::-1]

    experiment_plot = Instance(Component)
    par_count_plot  = Instance(Component)
    par_score_plot  = Instance(Component)
    par_dprime_plot = Instance(Component)

    @on_trait_change('data')
    def _generate_experiment_plot(self):
        plots = {}
        index_range = ChannelDataRange()
        index_range.sources = [self.data.spout_TTL]
        index_mapper = LinearMapper(range=index_range)

        container = OverlayPlotContainer(padding=[20, 20, 50, 50])

        value_range = DataRange1D(low_setting=-0, high_setting=1)
        value_mapper = LinearMapper(range=value_range)
        plot = TTLPlot(channel=self.data.spout_TTL, reference=0,
                index_mapper=index_mapper, value_mapper=value_mapper,
                fill_color=(0.25, 0.41, 0.88, 0.5), rect_center=0.25,
                rect_height=0.2)

        add_default_grids(plot, major_index=1, minor_index=0.25)
        add_time_axis(plot, orientation='top')
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

        plot = TTLPlot(channel=self.data.TO_TTL, reference=0,
                index_mapper=index_mapper, value_mapper=value_mapper,
                fill_color=(1, 0, 0, 0.5), line_color=(1, 0, 0, 1),
                line_width=1, rect_height=0.1, rect_center=0.125)
        container.add(plot)
        plots["Timeout Window"] = plot

        plot = TTLPlot(channel=self.data.TO_safe_TTL, reference=0,
                index_mapper=index_mapper, value_mapper=value_mapper,
                fill_color=(0, 0.5, 0, 0.25), line_color=(0, 0.5, 0, 1),
                line_width=1, rect_height=0.1, rect_center=0.125)
        container.add(plot)
        plots["Timeout Safe Window"] = plot

        #plot = TimeseriesPlot(series=self.data.trial_start_timestamp,
        #        index_mapper=index_mapper, value_mapper=value_mapper,
        #        line_color='black', line_width=2, label="Start Trial")
        #container.add(plot)

        #plot = TimeseriesPlot(series=self.data.trial_end_timestamp,
        #        index_mapper=index_mapper, value_mapper=value_mapper,
        #        line_color='black', line_width=2, label="End Trial")
        #container.add(plot)

        #plot = TimeseriesPlot(series=self.data.timeout_start_timestamp,
        #        index_mapper=index_mapper, value_mapper=value_mapper,
        #        line_color='red', line_width=2, label="Start TIMEOUT")
        #container.add(plot)

        #plot = TimeseriesPlot(series=self.data.timeout_end_timestamp,
        #        index_mapper=index_mapper, value_mapper=value_mapper,
        #        line_color='red', line_width=2, label="End TIMEOUT")
        #container.add(plot)

        self.experiment_plot = container

    @on_trait_change('data')
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

        add_default_grids(plot, major_value=5)
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
        
        add_default_grids(plot, minor_value=0.2)
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

    pump_group = VGroup(
            Item('handler.pump_toolbar', style='custom',
                 show_label=False), 
            Item('object.data.water_infused',
                 label='Dispensed (mL)', style='readonly'),
            Item('object.paradigm.pump_syringe'),
            Item('object.paradigm.pump_syringe_diameter', 
                 label='Diameter (mm)', style='readonly'),
            label='Pump Status',
            show_border=True,
            )

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
                show_label=False, width=1000, height=400),
            HGroup(
                Item('par_count_plot', editor=ComponentEditor(),
                    show_label=False, width=150, height=150),
                Item('par_score_plot', editor=ComponentEditor(),
                    show_label=False, width=150, height=150),
                Item('par_dprime_plot', editor=ComponentEditor(),
                    show_label=False, width=150, height=150)
                ),
            )

    experiment_group = VSplit(
            #VGroup(
            #    VGroup(
            #        Item('object.data.go_trial_count',
            #             label='Number of GO trials'),
            #        Item('object.data.nogo_trial_count',
            #             label='Number of NOGO trials'),
            #        Item('object.data.global_fa_frac',
            #             label='Global FA fraction'),
            #        show_border=True,
            #        ),
            #    VGroup(
            #        Item('object.data.mean_reaction_time',
            #             label='Mean'),
            #        Item('object.data.median_reaction_time',
            #             label='Median'),
            #        Item('object.data.var_reaction_time',
            #             label='Variance'),
            #        label='Reaction Time',
            #        show_border=True
            #        ),
            #    VGroup(
            #        Item('object.data.mean_response_time',
            #             label='Mean'),
            #        Item('object.data.median_response_time',
            #             label='Median'),
            #        Item('object.data.var_response_time',
            #             label='Variance'),
            #        label='Response Time',
            #        show_border=True,
            #        ),
            #    VGroup(
            #        Item('object.data.mean_react_to_resp_time',
            #             label='Mean'),
            #        Item('object.data.var_react_to_resp_time',
            #             label='Variance'),
            #        label='Response-Reaction Time',
            #        show_border=True,
            #        ),
            #    label='Experiment summary',
            #    show_border=True,
            #    style='readonly',
            #    ),
            #Item('trial_log_view', editor=trial_log_table),
            Item('object.data.par_info', editor=par_info_editor, height=150),
            Item('trial_log_view'),
            #Item('object.data.trial_log', editor=trial_log_table),
            show_labels=False,
            )

    traits_group = HSplit(
            VGroup(
                Item('handler.toolbar', style='custom'),
                Include('pump_group'),
                Include('status_group'),
                Item('paradigm', style='custom', editor=InstanceEditor()),
                show_labels=False,
            ),
            Include('plots_group'),
            Include('experiment_group'),
            show_labels=False,
        )

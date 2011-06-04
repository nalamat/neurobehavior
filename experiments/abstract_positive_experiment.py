from __future__ import division

import numpy as np
from enthought.traits.api import HasTraits, Any, Instance, DelegatesTo, \
        Int, Float, Property, on_trait_change, cached_property
from enthought.traits.ui.api import View, Item, VGroup, HGroup, InstanceEditor,\
    VSplit, HSplit, TabularEditor, Group, Include, Tabbed

from enthought.enable.api import Component, ComponentEditor

from analysis_plot_mixin import AnalysisPlotMixin


import cns

from abstract_experiment import AbstractExperiment
from positive_data import PositiveData

from enthought.chaco.api import DataRange1D, LinearMapper, PlotAxis, PlotGrid, \
        OverlayPlotContainer

from cns.chaco.channel_data_range import ChannelDataRange
from cns.chaco.ttl_plot import TTLPlot
from cns.chaco.timeseries_plot import TimeseriesPlot
from cns.chaco.dynamic_bar_plot import DynamicBarPlot, DynamicBarplotAxis
from cns.chaco.helpers import add_default_grids, add_time_axis

from enthought.traits.ui.api import VGroup, Item

from enthought.traits.ui.api import TabularEditor
from enthought.traits.ui.tabular_adapter import TabularAdapter

from enthought.traits.api import *

from colors import color_names

class ParInfoAdapter(TabularAdapter):

    color_map  = Dict
    parameters = List

    columns = [ ('P', 'parameter'),
                ('Hit %', 'hit_frac'), 
                ('FA %', 'fa_frac'),
                ('GO/NOGO', 'go_nogo_ratio'),
                ('GO #', 'go'),
                ('NOGO #', 'nogo'),
                ('HIT #', 'hit'),
                ('MISS #', 'miss'),
                ('FA #', 'fa'),
                ('CR #', 'cr'),
                ('d\'', 'd'),
                ('C', 'criterion'),
                (u'WD x\u0304', 'mean_react'),
                (u'WD x\u0303', 'median_react'),
                (u'WD \u03C3\u2093', 'std_react'),
                (u'RS x\u0304', 'mean_resp'),
                (u'RS x\u0303', 'median_resp'),
                (u'RS \u03C3\u2093', 'std_resp'),
                ]

    parameter_text = Property

    def _get_parameter_text(self):
        return ', '.join('{}'.format(p) for p in self._get_parameters())

    def _get_parameters(self):
        return [self.item[p] for p in self.parameters]

    def _get_bg_color(self):
        try:
            key = ', '.join('{}'.format(p) for p in self._get_parameters()[:-1])
            return self.color_map[key]
        except:
            return

class TrialLogAdapter(TabularAdapter):

    parameters = List(['parameter'])

    # List of tuples (column_name, field )
    columns = [ ('P',       'parameter'),
                ('S',       'speaker'),
                ('Time',    'time'),
                ('WD',      'reaction'),
                ('RS',      'response'), 
                ('WD',      'reaction_time'),
                ('RS',      'response_time')
                ]

    parameter_width = Float(75)
    reaction_width = Float(25)
    response_width = Float(25)
    speaker_width = Float(25)
    time_width = Float(65)
    reaction_time_width = Float(65)
    response_time_width = Float(65)
    response_image = Property
    reaction_image = Property

    parameter_text = Property
    speaker_text = Property
    time_text = Property

    def _get_parameter_text(self):
        return ', '.join('{}'.format(self.item[p]) for p in self.parameters)

    def _get_speaker_text(self):
        return self.item['speaker'][0].upper()

    def _get_time_text(self):
        seconds = self.item['start']
        return "{0}:{1:02}".format(*divmod(int(seconds), 60))

    def _get_bg_color(self):
        if self.item['ttype'] == 'GO':
            return color_names['light green']
        elif self.item['ttype'] == 'NOGO':
            return color_names['light red']
        else:
            return color_names['gray']

    def _get_reaction_image(self):
        if self.item['reaction'] == 'early':
            return '@icons:array_node'
        elif self.item['reaction'] == 'normal':
            return '@icons:tuple_node'
        else:
            return '@icons:none_node'

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

class AbstractPositiveExperiment(AbstractExperiment, AnalysisPlotMixin):

    index_range         = Any
    par_info_adapter    = ParInfoAdapter()
    par_info_editor     = TabularEditor(editable=False,
                                        adapter=par_info_adapter)

    trial_log_adapter   = TrialLogAdapter()
    trial_log_editor    = TabularEditor(editable=False,
                                        adapter=trial_log_adapter)
    trial_log_view      = Property(depends_on='data.trial_log',
                                   editor=trial_log_editor)

    @cached_property
    def _get_trial_log_view(self):
        # Allows us to ensure that last trial always appears at the top of the
        # list (otherwise we constantly need to scroll down to see the latest
        # trial).  Eventually we can add per-column sorting back in, but that is
        # a very low priority.
        return self.data.trial_log[::-1]

    experiment_plot = Instance(Component)

    def _add_behavior_plots(self, index_mapper, container):
        value_range = DataRange1D(low_setting=-0, high_setting=1)
        value_mapper = LinearMapper(range=value_range)
        plot = TTLPlot(channel=self.data.spout_TTL, reference=0,
                index_mapper=index_mapper, value_mapper=value_mapper,
                fill_color=(0.25, 0.41, 0.88, 0.5), rect_center=0.25,
                rect_height=0.2)
        container.add(plot)
        plot = TTLPlot(channel=self.data.signal_TTL, reference=0,
                index_mapper=index_mapper, value_mapper=value_mapper,
                fill_color=(0, 0, 0, 0.25), line_color=(0, 0, 0, 0.75),
                line_width=1, rect_height=0.3, rect_center=0.5)
        container.add(plot)
        plot = TTLPlot(channel=self.data.poke_TTL, reference=0,
                index_mapper=index_mapper, value_mapper=value_mapper,
                fill_color=(.17, .54, .34, 0.5), rect_center=0.75,
                rect_height=0.2)
        container.add(plot)
        plot = TTLPlot(channel=self.data.reaction_TTL, reference=0,
                index_mapper=index_mapper, value_mapper=value_mapper,
                fill_color=(1, 0, 0, 0.25), line_color=(1, 0, 0, 1),
                line_width=1, rect_height=0.1, rect_center=0.6)
        container.add(plot)
        plot = TTLPlot(channel=self.data.response_TTL, reference=0,
                index_mapper=index_mapper, value_mapper=value_mapper,
                fill_color=(0, 1, 0, 0.25), line_color=(0, 1, 0, 1),
                line_width=1, rect_height=0.1, rect_center=0.5)
        container.add(plot)
        plot = TTLPlot(channel=self.data.reward_TTL, reference=0,
                index_mapper=index_mapper, value_mapper=value_mapper,
                fill_color=(0, 0, 1, 0.25), line_color=(0, 0, 1, 1),
                line_width=1, rect_height=0.1, rect_center=0.4)
        container.add(plot)

    @on_trait_change('data')
    def _generate_experiment_plot(self):
        plots = {}
        index_range = ChannelDataRange()
        index_range.sources = [self.data.spout_TTL]
        index_mapper = LinearMapper(range=index_range)
        self.index_range = index_range

        container = OverlayPlotContainer(padding=[20, 20, 20, 50])

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

        self.experiment_plot = container

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
            Item('animal', style='readonly'),
            Item('handler.status', style='readonly'),
            Item('handler.current_poke_dur', 
                 label='Poke duration (s)', style='readonly'),
            Item('handler.current_setting_go', style='readonly',
                 label='Current GO'),
            label='Experiment',
            show_border=True,
            )

    plots_group = VSplit(
            VGroup(
                HGroup(HGroup('object.index_range.span')),
                Item('experiment_plot', editor=ComponentEditor(),
                    show_label=False, width=1000, height=300)
                ),
            Include('analysis_plot_group'),
            Item('object.data.par_info', editor=par_info_editor,
                label='Performance Statistics'),
            show_labels=False,
            )

    traits_group = HSplit(
            VGroup(
                Item('handler.toolbar', style='custom'),
                Include('pump_group'),
                Include('status_group'),
                Tabbed(
                    Item('paradigm', style='custom', editor=InstanceEditor()),
                    Include('context_group'),
                    show_labels=False,
                    ),
                show_labels=False,
            ),
            Include('plots_group'),
            VGroup(
                VGroup(
                    Item('object.data.global_fa_frac', label='Mean FA (frac)'),
                    Item('object.data.go_trial_count', label='Total GO'),
                    Item('object.data.nogo_trial_count', label='Total NOGO'),
                    Item('object.data.max_reaction_time', 
                        label='Slowest Mean Reaction Time (s)'),
                    Item('object.data.max_response_time', 
                        label='Slowest Mean Response Time (s)'),
                    label='Statistics Summary',
                    style='readonly',
                    show_border=True,
                    ),
                Tabbed(
                    Include('analysis_group'),
                    Item('trial_log_view', label='Trial log'),
                    show_labels=False,
                    ),
                show_labels=False,
                ),
            show_labels=False,
        )

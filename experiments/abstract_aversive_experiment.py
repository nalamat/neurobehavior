from numpy import clip

from enthought.traits.api import Instance, on_trait_change, Float, Property
from enthought.traits.ui.api import (View, Item, VGroup, HGroup, HSplit, Tabbed,
    Include)
from enthought.enable.api import Component, ComponentEditor
from enthought.chaco.api import DataRange1D, LinearMapper, PlotLabel, \
        VPlotContainer, PlotAxis, OverlayPlotContainer, Legend, ToolTip

from cns.chaco_exts.channel_data_range import ChannelDataRange
from cns.chaco_exts.channel_plot import ChannelPlot
from cns.chaco_exts.ttl_plot import TTLPlot
from cns.chaco_exts.timeseries_plot import TimeseriesPlot
from cns.chaco_exts.epoch_plot import EpochPlot
from cns.chaco_exts.dynamic_bar_plot import DynamicBarPlot, DynamicBarplotAxis
from cns.chaco_exts.helpers import add_default_grids, add_time_axis

from abstract_experiment import AbstractExperiment

import logging
log = logging.getLogger(__name__)

from enthought.traits.ui.api import TabularEditor
from enthought.traits.ui.tabular_adapter import TabularAdapter
from enthought.traits.api import *

from colors import color_names

class TrialLogAdapter(TabularAdapter):
    
    # List of tuples (column_name, field )
    columns = [ ('P',       'parameter'),
                #('S',       'speaker'),
                ('Time',    'time'),
                ('Score',   'contact_score'),
                ]

    parameter_width = Float(75)
    contact_score_width = Float(50)
    reaction_width = Float(25)
    response_width = Float(25)
    speaker_width = Float(25)
    time_width = Float(65)
    contact_score_image = Property

    parameter_text = Property
    speaker_text = Property
    time_text = Property
    contact_score_text = Property

    def _get_parameter_text(self):
        parameters = self.object.parameters
        return ', '.join('{}'.format(self.item[p]) for p in parameters)

    def _get_speaker_text(self):
        return self.item['speaker'][0].upper()

    def _get_time_text(self):
        seconds = self.item['start']
        return "{0}:{1:02}".format(*divmod(int(seconds), 60))

    def _get_bg_color(self):
        ttype = self.item['ttype']
        if ttype == 'NOGO':
            return color_names['light green']
        elif ttype == 'NOGO_REPEAT':
            return color_names['dark green']
        elif ttype == 'GO_REMIND':
            return color_names['dark red']
        elif ttype == 'GO':
            return color_names['light red']

    def _get_contact_score_image(self):
        if self.object.on_spout_seq[-(self.row+1)]:
            return '@icons:tuple_node'  # a green icon
        else:
            return '@icons:dict_node'   # a red icon

    def _get_contact_score_text(self):
        return str(self.object.contact_scores[-(self.row+1)])

class AbstractAversiveExperiment(AbstractExperiment):

    experiment_plot     = Instance(Component)

    @on_trait_change('data')
    def _update_experiment_plot(self):
        index_range = ChannelDataRange(trig_delay=0)
        index_range.sources = [self.data.contact_digital]
        index_mapper = LinearMapper(range=index_range)
        container = OverlayPlotContainer(padding=[20, 20, 50, 5])
        self._add_behavior_plots(index_mapper, container)
        # Add axes and grids to the first plot
        plot = container.components[0]
        add_default_grids(plot, minor_index=0.25, major_index=1)
        add_time_axis(plot, orientation='top')
        self.experiment_plot = container

    def _add_behavior_plots(self, index_mapper, container, alpha=0.25):
        value_range = DataRange1D(low_setting=0, high_setting=1)
        value_mapper = LinearMapper(range=value_range)
        plot = TTLPlot(channel=self.data.trial_running, reference=0,
                index_mapper=index_mapper, value_mapper=value_mapper,
                fill_color=(0.41, 0.88, 0.25, 0.5), rect_center=0.5,
                rect_height=0.8)
        container.add(plot)
        plot = TTLPlot(channel=self.data.shock_running, reference=0,
                index_mapper=index_mapper, value_mapper=value_mapper,
                fill_color=(0.88, 0.41, 0.25, 0.5), rect_center=0.5,
                rect_height=0.8)
        container.add(plot)
        plot = TTLPlot(channel=self.data.warn_running, reference=0,
                index_mapper=index_mapper, value_mapper=value_mapper,
                fill_color=(1.0, 0.25, 0.25, 0.75), rect_center=0.5,
                rect_height=0.8)
        container.add(plot)
        plot = TTLPlot(channel=self.data.contact_digital, reference=0,
                index_mapper=index_mapper, value_mapper=value_mapper,
                fill_color=(0.25, 0.41, 0.88, 0.75), rect_center=0.5,
                rect_height=0.5)
        container.add(plot)
        plot = ChannelPlot(channel=self.data.contact_digital_mean, reference=0,
                index_mapper=index_mapper, value_mapper=value_mapper,
                line_width=3)
        container.add(plot)
        plot = TimeseriesPlot(series=self.data.reaction_ts, marker='diamond',
                marker_color=(0, 1, 0, 1.0), marker_height=0.45,
                index_mapper=index_mapper, value_mapper=value_mapper)
        container.add(plot)
        plot = EpochPlot(series=self.data.spout_epoch, marker='diamond',
                marker_color=(.34, .54, .34, 1.0), marker_height=0.8,
                index_mapper=index_mapper, value_mapper=value_mapper)
        container.add(plot)
        plot = EpochPlot(series=self.data.trial_epoch, marker='diamond',
                marker_color=(.17, .54, .34, 1.0), marker_height=0.7,
                index_mapper=index_mapper, value_mapper=value_mapper)
        container.add(plot)

    traits_group = HSplit(
            VGroup(
                Item('handler.toolbar', style='custom'),
                VGroup(
                    Item('animal', show_label=False),
                    Item('handler.status', label='Status'),
                    label='Experiment',
                    style='readonly',
                    show_border=True,
                    ),
                VGroup(
                    Item('handler.pump_toolbar', style='custom',
                         show_label=False), 
                    Item('object.data.water_infused',
                         label='Dispensed (mL)', style='readonly'),
                    Item('object.paradigm.pump_rate'),
                    Item('object.paradigm.pump_syringe'),
                    Item('object.paradigm.pump_syringe_diameter', 
                         label='Diameter (mm)', style='readonly'),
                    label='Pump Status',
                    show_border=True,
                    ),
                # Include the GUI from the paradigm
                Tabbed(
                    Item('paradigm', style='custom', show_label=False), 
                    Include('context_group'), # defined in abstract_experiment
                    ),
                show_labels=False,
                ),
            VGroup(
                Item('experiment_plot', editor=ComponentEditor(),
                    show_label=False, width=1000, height=150),
                Include('analysis_plot_group'),
                show_labels=False,
                ),
            Tabbed(
                Item('object.data.summary_trial_log', width=200,
                    editor=TabularEditor(editable=False,
                        adapter=TrialLogAdapter())),
                Include('analysis_settings_group'),
                VGroup(
                    VGroup(
                        Item('object.data.mask_mode'),
                        Item('object.data.include_last'), 
                        Item('object.data.exclude_first'),
                        Item('object.data.exclude_last'),
                        label='Mask settings',
                        show_border=True,
                        ),
                    VGroup(
                         Item('object.data.contact_offset',
                             label='Contact offset (s)'),
                         Item('object.data.contact_dur', 
                             label='Contact duration (s)'),
                         Item('object.data.contact_reference'),
                        label='Contact settings',
                        show_border=True,
                         ),
                   label='Analysis Parameters',
                   ),
                show_labels=False,
                ),
            show_labels=False,
            )

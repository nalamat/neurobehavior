from __future__ import division

import traceback
import threading
from traits.api import Any, Instance, \
        Int, Float, Property, on_trait_change, cached_property
from traitsui.api import Item, VGroup, InstanceEditor,\
    HSplit, TabularEditor, Include, Tabbed, ShellEditor

from enable.api import Component, ComponentEditor
from abstract_experiment import AbstractExperiment

from chaco.api import DataRange1D, LinearMapper, \
        OverlayPlotContainer

from cns.chaco_exts.channel_range_tool import ChannelRangeTool
from cns.chaco_exts.channel_data_range import ChannelDataRange
from cns.chaco_exts.extremes_channel_plot import ExtremesChannelPlot
from cns.chaco_exts.helpers import add_default_grids, add_time_axis
from cns.chaco_exts.tables_timeseries_plot import TablesTimeseriesPlot
from cns.chaco_exts.epoch_rect_plot import EpochRectPlot

from cns import get_config
COLORS = get_config('EXPERIMENT_COLORS')

from traitsui.tabular_adapter import TabularAdapter

class TrialLogAdapter(TabularAdapter):

    columns = [ ('P',       'parameter'),
                ('Time',    'time'),
                ('score',   'score'),
                ('WD',      'reaction_time'),
                ('RS',      'response_time')
                ]

    parameter_width = Float(75)
    response_width = Float(25)
    time_width = Float(65)
    reaction_time_width = Float(65)
    response_time_width = Float(65)
    parameter_text = Property
    time_text = Property

    def get_item(self, object, trait, row):
        dataframe = getattr(object, trait)
        if len(dataframe) == 0:
            return None
        return dataframe.iloc[-row-1] # Reverse order

    def _get_parameter_text(self):
        parameters = self.object.parameters
        return ', '.join('{}'.format(self.item[p]) for p in parameters)

    def _get_time_text(self):
        seconds = self.item['target_start']
        return "{0}:{1:02}".format(*divmod(int(seconds), 60))

    def _get_bg_color(self):
        return COLORS[self.item['ttype']]


class AbstractPositiveExperiment(AbstractExperiment):

    experiment_plot = Instance(Component)

    def _add_experiment_plots(self, index_mapper, container, alpha=0.25):

        # microphone and speaker plots
        value_range = DataRange1D(low_setting=-4, high_setting=1.5)
        value_mapper = LinearMapper(range=value_range)

        plot = ExtremesChannelPlot(source=self.data.mic, line_color='black',
            index_mapper=index_mapper, value_mapper=value_mapper)
        self.mic_plot = plot

        container.add(plot)
        plot = ExtremesChannelPlot(source=self.data.speaker, line_color='green',
            index_mapper=index_mapper, value_mapper=value_mapper)
        container.add(plot)


        # target, pump and timeout rectangle epoch plots
        value_range = DataRange1D(low_setting=0, high_setting=1)
        value_mapper = LinearMapper(range=value_range)

        plot = EpochRectPlot(source=self.data.target_epoch,
            rect_color=(0,1,0,.5), rect_ypos=0.35, rect_height=0.2,
            index_mapper=index_mapper, value_mapper=value_mapper)
        container.add(plot)

        plot = EpochRectPlot(source=self.data.pump_epoch,
            rect_color=(0,0,1,.5), rect_ypos=0.35, rect_height=0.2,
            index_mapper=index_mapper, value_mapper=value_mapper)
        container.add(plot)

        plot = EpochRectPlot(source=self.data.timeout_epoch,
            rect_color=(1,0,0,.5), rect_ypos=0.35, rect_height=0.2,
            index_mapper=index_mapper, value_mapper=value_mapper)
        container.add(plot)


        # poke and spout analog plots
        value_range = DataRange1D(low_setting=-1, high_setting=16)
        value_mapper = LinearMapper(range=value_range)

        plot = ExtremesChannelPlot(source=self.data.poke, line_color='orange',
            index_mapper=index_mapper, value_mapper=value_mapper)
        container.add(plot)

        plot = ExtremesChannelPlot(source=self.data.spout, line_color='blue',
            index_mapper=index_mapper, value_mapper=value_mapper)
        container.add(plot)


        # poke, spout and button epoch marker plots
        value_range = DataRange1D(low_setting=0, high_setting=2)
        value_mapper = LinearMapper(range=value_range)

        kw = {'source':self.data, 'trait_name':'event_log',
            'changed_name':'event_log_updated', 'index_mapper':index_mapper,
            'value_mapper':value_mapper, 'marker_size':8, 'marker_edge_width':0}

        plot = TablesTimeseriesPlot(event_name='initiated nose poke',
            marker='triangle', marker_color='orange', **kw)
        container.add(plot)
        plot = TablesTimeseriesPlot(event_name='withdrew from nose poke',
            marker='inverted_triangle', marker_color='orange', **kw)
        container.add(plot)

        plot = TablesTimeseriesPlot(event_name='spout contact',
            marker='triangle', marker_color='blue', **kw)
        container.add(plot)
        plot = TablesTimeseriesPlot(event_name='withdrew from spout',
            marker='inverted_triangle', marker_color='blue', **kw)
        container.add(plot)

        plot = TablesTimeseriesPlot(event_name='push button pressed',
            marker='triangle', marker_color='brown', **kw)
        container.add(plot)
        plot = TablesTimeseriesPlot(event_name='push button released',
            marker='inverted_triangle', marker_color='brown', **kw)
        container.add(plot)


        tool = ChannelRangeTool(component=plot, allow_drag=False, value_factor=1)
        plot.tools.append(tool)

    @on_trait_change('data')
    def _generate_experiment_plot(self):
        try:
            index_range = ChannelDataRange(trig_delay=0)
            index_range.sources = [self.data.mic]
            index_mapper = LinearMapper(range=index_range)
            self.index_range = index_range
            container = OverlayPlotContainer(padding=[20, 20, 50, 5])
            self._add_experiment_plots(index_mapper, container, 0.5)
            plot = container.components[0]
            add_default_grids(plot, major_index=1, minor_index=0.25)
            add_time_axis(plot, orientation='top')
            self.experiment_plot = container
        except:
            log.error(traceback.format_exc())
            raise

    status_group = VGroup(
            Item('animal'),
            Item('handler.status'),
            label='Experiment',
            show_border=True,
            style='readonly'
            )

    plots_group = VGroup(
            Item('experiment_plot', editor=ComponentEditor(), show_label=False,
                width=1000, height=300),
            Include('analysis_plot_group'),
            show_labels=False,
            label='Experiment overview',
            )

    experiment_summary_group = VGroup(
        label='Experiment Summary',
        style='readonly',
        show_border=True,
        )

    traits_group = HSplit(
            VGroup(
                Item('handler.toolbar', style='custom'),
                Include('status_group'),
                Tabbed(
                    Item('paradigm', style='custom', editor=InstanceEditor(),
                         label='Settings'),
                    Include('context_group'),
                    show_labels=False,
                    ),
                show_labels=False,
            ),
            Tabbed(
                Include('plots_group'),
                # Handler is a reference to the controller class.  In this case,
                # the subclass AbstractPositiveController defined in the
                # paradigm file.
                Item('handler.shell_variables', editor=ShellEditor(),
                     label='Python shell'),
                show_labels=False,
                ),
            VGroup(
                Include('experiment_summary_group'),
                VGroup(
                    label='Analysis settings',
                    show_border=True,
                    ),
                Tabbed(
                    Item('object.data.trial_log', label='Trial log',
                         editor=TabularEditor(editable=False,
                                              adapter=TrialLogAdapter())),
                    Include('analysis_settings_group'),
                    show_labels=False,
                    ),
                show_labels=False,
                ),
            show_labels=False,
        )

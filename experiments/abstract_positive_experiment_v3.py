from __future__ import division

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
        return dataframe.iloc[row]

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

        # set up microphone plot
        value_range = DataRange1D(low_setting=-4.5, high_setting=1.5)
        value_mapper = LinearMapper(range=value_range)
        plot = ExtremesChannelPlot(source=self.data.microphone,
                           index_mapper=index_mapper, value_mapper=value_mapper,
                           line_color='black')
        self.microphone_plot = plot
        container.add(plot)

        # set up nose poke plot
        value_range = DataRange1D(low_setting=-.5, high_setting=10.5)
        value_mapper = LinearMapper(range=value_range)
        plot = ExtremesChannelPlot(source=self.data.np,
                           index_mapper=index_mapper, value_mapper=value_mapper,
                           line_color='blue')
        container.add(plot)
        
        # set up lick spout plot
#        value_range = DataRange1D(low_setting=-.5, high_setting=10.5)
#        value_mapper = LinearMapper(range=value_range)
        plot = ExtremesChannelPlot(source=self.data.spout,
                           index_mapper=index_mapper, value_mapper=value_mapper,
                           line_color='orange')
        container.add(plot)
        
        # set up epoch plot
        value_range = DataRange1D(low_setting=-0, high_setting=1)
        value_mapper = LinearMapper(range=value_range)

        plot = TablesTimeseriesPlot(source=self.data,
                                    trait_name='event_log',
                                    changed_name='event_log_updated',
                                    event_name='initiated nose poke',
                                    marker='diamond',
                                    marker_color='black',
                                    marker_height=0.45,
                                    index_mapper=index_mapper,
                                    value_mapper=value_mapper)
        container.add(plot)

        plot = TablesTimeseriesPlot(source=self.data,
                                    trait_name='event_log',
                                    changed_name='event_log_updated',
                                    event_name='withdrew from nose poke',
                                    marker='diamond',
                                    marker_color='red',
                                    marker_height=0.45,
                                    index_mapper=index_mapper,
                                    value_mapper=value_mapper)
        container.add(plot)

        plot = TablesTimeseriesPlot(source=self.data,
                                    trait_name='event_log',
                                    changed_name='event_log_updated',
                                    event_name='spout contact',
                                    marker='diamond',
                                    marker_color='yellow',
                                    marker_height=0.45,
                                    index_mapper=index_mapper,
                                    value_mapper=value_mapper)
        container.add(plot)

        plot = TablesTimeseriesPlot(source=self.data,
                                    trait_name='event_log',
                                    changed_name='event_log_updated',
                                    event_name='withdrew from spout',
                                    marker='diamond',
                                    marker_color='green',
                                    marker_height=0.45,
                                    index_mapper=index_mapper,
                                    value_mapper=value_mapper)
        container.add(plot)

        tool = ChannelRangeTool(component=plot, allow_drag=False,
                value_factor=1)
        plot.tools.append(tool)
        

    @on_trait_change('data')
    def _generate_experiment_plot(self):
        index_range = ChannelDataRange(trig_delay=0)
        index_range.sources = [self.data.microphone]
        index_mapper = LinearMapper(range=index_range)
        self.index_range = index_range
        container = OverlayPlotContainer(padding=[20, 20, 50, 5])
        self._add_experiment_plots(index_mapper, container, 0.5)
        plot = container.components[0]
        add_default_grids(plot, major_index=1, minor_index=0.25)
        add_time_axis(plot, orientation='top')
        self.experiment_plot = container

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
                VGroup(
                    label='Experiment Summary',
                    style='readonly',
                    show_border=True,
                    ),
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

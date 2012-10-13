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
from cns.chaco_exts.ttl_plot import TTLPlot
from cns.chaco_exts.timeseries_plot import TimeseriesPlot
from cns.chaco_exts.epoch_plot import EpochPlot
from cns.chaco_exts.rms_channel_plot import RMSChannelPlot
from cns.chaco_exts.helpers import add_default_grids, add_time_axis

from cns import get_config
COLORS = get_config('EXPERIMENT_COLORS')

from traitsui.tabular_adapter import TabularAdapter

class TrialLogAdapter(TabularAdapter):

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
        parameters = self.object.data.parameters
        return ', '.join('{}'.format(self.item[p]) for p in parameters)

    def _get_speaker_text(self):
        return self.item['speaker'][0].upper()

    def _get_time_text(self):
        seconds = self.item['start']
        return "{0}:{1:02}".format(*divmod(int(seconds), 60))

    def _get_bg_color(self):
        return COLORS[self.item['ttype']]

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

class AbstractPositiveExperiment(AbstractExperiment):

    microphone_plot = Instance(Component)
    experiment_plot = Instance(Component)
    trial_log_adapter = TrialLogAdapter()
    trial_log_editor = TabularEditor(editable=False, adapter=trial_log_adapter,
            dclicked='selected_trial_event')
    trial_log_view = Property(depends_on='data.trial_log',
            editor=trial_log_editor)

    selected_trial_event = Any
    selected_trial = Property(Int, depends_on='selected_trial_event')

    def _get_selected_trial(self):
        return len(self.data.trial_log)-self.selected_trial_event.row-1

    @cached_property
    def _get_trial_log_view(self):
        # Reverse the list (this compensates for a bug in Enthought's
        # Qt implementation of the TabularEditor (TODO submit patch for this
        # bug)
        return self.data.trial_log[::-1]

    def _add_experiment_plots(self, index_mapper, container, alpha=0.25):
        value_range = DataRange1D(low_setting=-0, high_setting=1)
        value_mapper = LinearMapper(range=value_range)
        plot = TTLPlot(source=self.data.spout_TTL, reference=0,
                index_mapper=index_mapper, value_mapper=value_mapper,
                fill_color=(0.25, 0.41, 0.88, alpha), line_width=1,
                rect_center=0.25, rect_height=0.2)
        container.add(plot)
        plot = TTLPlot(source=self.data.signal_TTL, reference=0,
                index_mapper=index_mapper, value_mapper=value_mapper,
                fill_color=(0, 0, 0, alpha), line_color=(0, 0, 0, 0.75),
                line_width=1, rect_height=0.3, rect_center=0.5)
        container.add(plot)
        plot = TTLPlot(source=self.data.poke_TTL, reference=0,
                index_mapper=index_mapper, value_mapper=value_mapper,
                fill_color=(.17, .54, .34, alpha), rect_center=0.75,
                line_width=1, rect_height=0.2)
        container.add(plot)
        plot = TTLPlot(source=self.data.reaction_TTL, reference=0,
                index_mapper=index_mapper, value_mapper=value_mapper,
                fill_color=(1, 0, 0, alpha), line_color=(1, 0, 0, 1),
                line_width=1, rect_height=0.1, rect_center=0.6)
        container.add(plot)
        plot = TTLPlot(source=self.data.response_TTL, reference=0,
                index_mapper=index_mapper, value_mapper=value_mapper,
                fill_color=(0, 1, 0, alpha), line_color=(0, 1, 0, 1),
                line_width=1, rect_height=0.1, rect_center=0.5)
        container.add(plot)
        plot = TTLPlot(source=self.data.reward_TTL, reference=0,
                index_mapper=index_mapper, value_mapper=value_mapper,
                fill_color=(0, 0, 1, alpha), line_color=(0, 0, 1, 1),
                line_width=1, rect_height=0.1, rect_center=0.4)
        container.add(plot)
        plot = TTLPlot(source=self.data.TO_TTL, reference=0,
                index_mapper=index_mapper, value_mapper=value_mapper,
                fill_color=(1, 0, 0, alpha), line_color=(1, 0, 0, 1),
                line_width=1, rect_height=0.1, rect_center=0.1)
        container.add(plot)
        plot = TimeseriesPlot(source=self.data.response_ts, marker='diamond',
                marker_color=(0, 1, 0, 1.0), marker_height=0.45,
                index_mapper=index_mapper, value_mapper=value_mapper)
        container.add(plot)
        plot = EpochPlot(source=self.data.all_poke_epoch, marker='diamond',
                marker_color=(.34, .54, .34, 1.0), marker_height=0.8,
                index_mapper=index_mapper, value_mapper=value_mapper)
        container.add(plot)
        plot = EpochPlot(source=self.data.poke_epoch, marker='diamond',
                marker_color=(.17, .54, .34, 1.0), marker_height=0.7,
                index_mapper=index_mapper, value_mapper=value_mapper)
        container.add(plot)
        plot = EpochPlot(source=self.data.signal_epoch, marker='diamond',
                marker_color=(0.5, 0.5, 0.5, 1.0), marker_height=0.6, 
                index_mapper=index_mapper, value_mapper=value_mapper)
        container.add(plot)
        plot = EpochPlot(source=self.data.trial_epoch, marker='diamond',
                marker_color=(0.75, 0.25, 0.75, 1.0), marker_height=0.5, 
                index_mapper=index_mapper, value_mapper=value_mapper)
        container.add(plot)

        tool = ChannelRangeTool(component=plot, allow_drag=False,
                value_factor=1)
        plot.tools.append(tool)

        # set up microphone plot
        value_range = DataRange1D(low_setting=0, high_setting=80)
        value_mapper = LinearMapper(range=value_range)
        plot = RMSChannelPlot(source=self.data.microphone,
                index_mapper=index_mapper, value_mapper=value_mapper,
                line_color=(0, 0, 0, 0.25))
        self.microphone_plot = plot
        container.add(plot)

    @on_trait_change('data')
    def _generate_experiment_plot(self):
        index_range = ChannelDataRange(trig_delay=0)
        index_range.sources = [self.data.spout_TTL]
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
                Item('handler.pump_toolbar', style='custom'),
                Item('object.microphone_plot.sensitivity', show_label=True),
                Item('object.microphone_plot.input_gain', show_label=True),
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
                    Item('object.data.global_fa_frac', label='Mean FA (frac)'),
                    Item('object.data.go_trial_count', label='Total GO'),
                    Item('object.data.nogo_trial_count', label='Total NOGO'),
                    Item('object.data.water_infused', 
                        label='Water dispensed (mL)'),
                    label='Experiment Summary',
                    style='readonly',
                    show_border=True,
                    ),
                VGroup(
                    Item('object.data.mask_mode'),
                    Item('object.data.mask_num'),
                    label='Analysis settings',
                    show_border=True,
                    ),
                Tabbed(
                    Item('trial_log_view', label='Trial log'),
                    Include('analysis_settings_group'),
                    show_labels=False,
                    ),
                show_labels=False,
                ),
            show_labels=False,
        )

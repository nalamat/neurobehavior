import numpy as np
from enable.api import Component, ComponentEditor
from traits.api import Instance, Int, on_trait_change, \
        Dict, HasTraits, Any, List, Str, Enum, Property
from traitsui.api import VGroup, Item, EnumEditor, SetEditor, HGroup

from cns.chaco_exts.helpers import add_default_grids

from chaco.api import DataRange1D, LinearMapper, \
        PlotAxis, LogMapper, ArrayDataSource, \
        OverlayPlotContainer, LinePlot, ScatterPlot

from traitsui.api import TabularEditor
from traitsui.tabular_adapter import TabularAdapter

from cns import get_config

CHACO_AXES_PADDING = get_config('CHACO_AXES_PADDING')
PAIRED_COLORS_NORM = get_config('PAIRED_COLORS_RGB_NORM')

class ParInfoAdapter(TabularAdapter):

    columns = [
        ('Parameter(s)', 'parameter'),
        ('Hit rate', 'hit_rate'),
        ('FA rate', 'fa_rate'),
        ('Trials', 'trials'),
        ('Reaction time', 'median_reaction_time'),
        ('Response time', 'median_response_time'),
        ('D prime', 'z_score'),
    ]

    parameter_text  = Property

    def get_item(self, object, trait, row):
        dataframe = getattr(object, trait)
        if dataframe is None or len(dataframe) == 0:
            return None
        return dataframe.iloc[row]

    def _get_parameter_text(self):
        return str(self.item.name)


class CLExperimentMixin(HasTraits):

    index_range         = Any
    par_info_adapter    = ParInfoAdapter()
    par_info_editor     = TabularEditor(editable=False,
                                        adapter=par_info_adapter)

    plot_1 = Instance(Component)
    plot_data = Instance(ArrayDataSource, ())
    plot_range = Dict(Str, Instance(DataRange1D))
    color_index = Int(0)
    color_map = Dict

    # Plotting and analysis options
    plot_index = Str(plot_setting=True)
    plot_group = List([], plot_setting=True)
    index_scale = Enum('log', 'linear', plot_setting=True)

    parameter_info      = Dict
    available_statistics = Dict

    def _parameter_info_default(self):
        traits = self.paradigm.traits(log=True)
        return dict((name, trait.label) for name, trait in traits.items())

    @on_trait_change('+plot_setting')
    def _generate_summary_plots(self):
        if self.traits_inited():
            # Clear the plot data
            self.color_index = 0
            self.color_map = {}
            self.plot_range = { 'pars': DataRange1D() }

            self.plot_1 = self._create_plot_container()
            #self.plot_2 = self._create_plot_container(self.plot_2_value)
            #self.plot_3 = self._create_plot_container(self.plot_3_value)
            self._update()

    def _create_plot_container(self):
        container_class = OverlayPlotContainer
        container_kw = dict(padding=CHACO_AXES_PADDING, spacing=5, bgcolor='white')
        value_range = DataRange1D(low=-1, high=3)
        self.plot_range[value] = value_range
        return container_class(**container_kw)

    def _add_default_axes_and_grids(self, plot, value):
        value_trait = self.data.trait(value)
        axis = PlotAxis(plot, orientation='left', title=value_trait.label)
        plot.overlays.append(axis)

        index_title = self.paradigm.get_parameter_label(self.data.parameters[-1])
        axis = PlotAxis(plot, orientation='bottom', title=index_title)
        plot.overlays.append(axis)

        minor, major = value_trait.suggested_grid
        add_default_grids(plot, minor_value=minor, major_value=major)

    @on_trait_change('data.trial_log')
    def _update(self):
        self._update_data_categories('parameters', self.plot_1)

    def _update_data_categories(self, index_name, component):
        return
        performance = self.data.performance
        if performance.index.nlevels != 1:
            levels = performance.index.names[1:]
            for category, df in performance.groupby(level=levels):
                category_name = ', '.join(str(c) for c in category)
                self.plot_data.set_data(category_name+'_index', df.index)
                self.plot_data.set_data(category_name+'_value', df['z_score'])

                if category_name in self.color_map:
                    plot_color = self.color_map[category_name]
                else:
                    self.color_index += 1
                    plot_color = PAIRED_COLORS_NORM[-self.color_index]
                    # For some reason the par_info_adapter color map requires
                    # the color to be scaled to 255
                    plot_color_255 = tuple(255.0*c for c in plot_color)
                    self.color_map[category_name] = plot_color
                    self.par_info_adapter.color_map[category_name] = plot_color_255


                #index_range = self.plot_range[index_name]
                #index_range.add(index_data)
                #value_range = self.plot_range[value_name]
                #value_range.add(value_data)

                #if self.index_scale == 'log':
                #    index_mapper = LogMapper(range=index_range)
                #else:
                #    index_mapper = LinearMapper(range=index_range)
                #value_mapper = LinearMapper(range=value_range)

                # Create the line plot
                overlay = component

                p = LinePlot(index=index_data, value=value_data,
                        index_mapper=index_mapper, value_mapper=value_mapper,
                        line_width=5, color=plot_color)
                overlay.add(p)

                # Create the points for the line plot (i.e. scatter)
                p = ScatterPlot(index=index_data, value=value_data,
                        index_mapper=index_mapper, value_mapper=value_mapper,
                        marker='circle', outline_color='white',
                        marker_size=10, line_width=2, color=plot_color)
                overlay.add(p)

                # Note that for each category, we add 2 components (the line #
                # and scatter).
                if len(component.components) == 2:
                    self._add_default_axes_and_grids(p, value_name)

    analysis_plot_group = VGroup(
            #HGroup(
            #    Item('plot_1', editor=ComponentEditor(), width=150, height=400),
            #    show_labels=False,
            #),
            Item('object.data.performance', editor=par_info_editor),
            show_labels=False,
            )

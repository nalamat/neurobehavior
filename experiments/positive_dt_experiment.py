import numpy as np
from enthought.traits.api import Instance, Int, on_trait_change, \
        Dict, HasTraits, Any, List, Str, Enum, Property
from enthought.traits.ui.api import View, Include, VSplit, HSplit, \
        VGroup, Item, InstanceEditor, EnumEditor, SetEditor

from abstract_positive_experiment import AbstractPositiveExperiment
from positive_dt_paradigm import PositiveDTParadigm
from positive_dt_controller import PositiveDTController

from positive_dt_data import PositiveDTData

from cns.chaco.helpers import add_default_grids

from enthought.chaco.api import Plot, DataRange1D, LinearMapper, \
        PlotAxis, ArrayPlotData, Legend, LogMapper, ArrayDataSource, \
        OverlayPlotContainer, LinePlot, ScatterPlot, BarPlot, \
        VPlotContainer

from colors import paired_colors, paired_colors_255

class PositiveDTExperiment(AbstractPositiveExperiment):

    paradigm            = Instance(PositiveDTParadigm, ())
    plot_data           = Dict(Str, Instance(ArrayDataSource))
    plot_range          = Dict(Str, Instance(DataRange1D))
    color_index         = Int(0)
    color_map           = Dict

    group_mode          = Enum('overlay', 'stack')

    # Plotting and analysis options
    available_group     = Property(depends_on='paradigm.parameters, plot_index')
    plot_index          = Str()
    plot_group          = List([])
    index_scale         = Enum('log', 'linear', plot_setting=True)
    plot_1_value        = Str('par_go_count', plot_setting=True)
    plot_2_value        = Str('par_hit_frac', plot_setting=True)
    plot_3_value        = Str('par_dprime', plot_setting=True)

    @on_trait_change('plot_index, plot_group')
    def _update_analysis_parameters(self):
        parameters = self.plot_group[:]
        parameters.append(self.plot_index)
        self.data.parameters = parameters
        self._generate_summary_plots()

    PLOT_VALUE_EDITOR   = EnumEditor(name='object.data.available_statistics')
    PLOT_INDEX_EDITOR   = EnumEditor(name='object.paradigm.parameter_info')
    PLOT_GROUP_EDITOR   = SetEditor(name='available_group',
                                    left_column_title='Available',
                                    right_column_title='Selected',
                                    can_move_all=False,
                                    ordered=True,
                                    )

    analysis_group = VGroup(
            VGroup(
                Item('plot_index', editor=PLOT_INDEX_EDITOR),
                Item('index_scale'),
                Item('plot_1_value', editor=PLOT_VALUE_EDITOR),
                Item('plot_2_value', editor=PLOT_VALUE_EDITOR),
                Item('plot_3_value', editor=PLOT_VALUE_EDITOR),
                label='Plot options',
                show_border=True,
                ),
            VGroup(
                Item('plot_group', editor=PLOT_GROUP_EDITOR, show_label=False),
                label='Category options',
                show_border=True,
                ),
            label='Analysis options',
            )

    def _plot_index_changed(self, new):
        if new in self.plot_group:
            self.plot_group.remove(new)

    def _get_available_group(self):
        info = self.paradigm.parameter_info
        try:
            del info[self.plot_index]
        except:
            pass
        return info

    def _update_data_categories(self, index_name, value_name, component):
        plot_name = index_name+value_name
        index = self.data.get_data(index_name)
        value = self.data.get_data(value_name)
        categories = [p[:-1] for p in index]
        unique_categories = sorted(set(categories))

        for category in unique_categories:
            mask = np.array([c==category for c in categories])
            mask = np.flatnonzero(mask)
            category_index = [p[-1] for p in np.take(index, mask)]
            category_value = np.take(value, mask)
            if type(category) in (tuple, list):
                category_name = ', '.join([str(e) for e in category])
            else:
                category_name = str(category)

            if category_name+value_name+plot_name in self.plot_data:
                self.plot_data[category_name+index_name+plot_name].set_data(category_index)
                self.plot_data[category_name+value_name+plot_name].set_data(category_value)
            else:
                # This is a new category.  Let's add the plot.  First, check to
                # see if we have already assigned a color to this category.
                index_data = ArrayDataSource(category_index)
                self.plot_data[category_name+index_name+plot_name] = index_data
                value_data = ArrayDataSource(category_value)
                self.plot_data[category_name+value_name+plot_name] = value_data

                if category_name in self.color_map:
                    plot_color = self.color_map[category_name]
                else:
                    self.color_index += 1
                    plot_color = paired_colors[-self.color_index]
                    plot_color_255 = paired_colors_255[-self.color_index]
                    self.color_map[category_name] = plot_color
                    self.par_info_adapter.color_map[category_name] = plot_color_255

                index_range = self.plot_range[index_name]
                index_range.add(index_data)
                value_range = self.plot_range[value_name]
                value_range.add(value_data)

                if self.index_scale == 'log':
                    index_mapper = LogMapper(range=index_range)
                else:
                    index_mapper = LinearMapper(range=index_range)
                value_mapper = LinearMapper(range=value_range)

                # Create the line plot
                if self.group_mode == 'stack':
                    overlay = OverlayPlotContainer()
                    component.add(overlay)
                else:
                    overlay = component

                p = LinePlot(index=index_data, value=value_data,
                        index_mapper=index_mapper, value_mapper=value_mapper,
                        line_width=5, color=plot_color)
                overlay.add(p)
                # Create the points for the line plot (i.e. scatter)
                p = ScatterPlot(index=index_data, value=value_data,
                        index_mapper=index_mapper, value_mapper=value_mapper,
                        marker='circle', outline_color='white',
                        marker_size=10-self.color_index,
                        line_width=2, color=plot_color)
                overlay.add(p)

                #if self.group_mode == 'stack':
                if self.group_mode == 'stack':
                    p.overlays.append(PlotAxis(p, orientation='left',
                        small_haxis_style=True, title=category_name))
                    if len(component.components) == 1:
                        p.overlays.append(PlotAxis(p, orientation='bottom',
                            small_haxis_style=False))
                else: 
                    # Note that for each category, we add 2 components (the line
                    # and scatter).
                    if len(component.components) == 2:
                        self._add_default_axes_and_grids(p, value_name)

    @on_trait_change('data.trial_log')
    def _update(self):
        self._update_data_categories('pars', self.plot_1_value, self.plot_1)
        self._update_data_categories('pars', self.plot_2_value, self.plot_2)
        self._update_data_categories('pars', self.plot_3_value, self.plot_3)

    @on_trait_change('+plot_setting')
    def _generate_summary_plots(self):
        # Clear the plot data
        self.color_index = 0
        self.color_map = {}
        self.plot_data = {}
        self.plot_range = { 'pars': DataRange1D() }

        self.plot_1 = self._create_plot_container(self.plot_1_value)
        self.plot_2 = self._create_plot_container(self.plot_2_value)
        self.plot_3 = self._create_plot_container(self.plot_3_value)
        self._update()

    def _create_plot_container(self, value):
        if self.group_mode == 'stack':
            container_class = VPlotContainer
        else:
            container_class = OverlayPlotContainer

        container_kw = dict(padding=(25, 5, 5, 25), spacing=10, bgcolor='white')

        range_hint = self.data.PLOT_RANGE_HINTS.get(value, {})
        value_range = DataRange1D(**range_hint)
        self.plot_range[value] = value_range
        return container_class(**container_kw)

    def _add_default_axes_and_grids(self, plot, value):
        axis = PlotAxis(plot, orientation='left')
        plot.overlays.append(axis)
        axis = PlotAxis(plot, orientation='bottom')
        plot.overlays.append(axis)

        grid_kw = self.data.PLOT_GRID_HINTS.get(value, {})
        add_default_grids(plot, **grid_kw)

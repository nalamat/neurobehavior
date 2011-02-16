import numpy as np
from enthought.traits.api import Instance, Int, on_trait_change, \
        Dict, HasTraits, Any, List, Str
from enthought.traits.ui.api import View, Include, VSplit, HSplit, \
        VGroup, Item, InstanceEditor

from abstract_positive_experiment import AbstractPositiveExperiment
from positive_dt_paradigm import PositiveDTParadigm
from positive_dt_controller import PositiveDTController

from positive_dt_data import PositiveDTData

from enthought.chaco.api import Plot, DataRange1D, LinearMapper, \
        PlotAxis, ArrayPlotData, Legend, LogMapper, ArrayDataSource, \
        OverlayPlotContainer, LinePlot, ScatterPlot, BarPlot, \
        VPlotContainer, PlotGrid
from cns.chaco.dynamic_bar_plot import DynamicBarPlot, DynamicBarplotAxis

from enthought.chaco.default_colors import cbrewer
COLOR_PALETTE = ['cadetblue', 'springgreen', 'red', 'pink', 'darkgray', 'silver']

from enthought.traits.ui.api import TableEditor, ObjectColumn

class LegendColumn(ObjectColumn):

    def get_cell_color(self, object):
        return object.color

    def get_value(self, object):
        return object.label

class ColorCategory(HasTraits):

    color = Any
    label = Any

    def __cmp__(self, other):
        return cmp(self.label, other.label)

legend_table = TableEditor(
        editable=False,
        columns = [LegendColumn(name='label')]
        )

def add_default_grids(plot, 
        major_index_spacing=1,
        minor_index_spacing=None,
        major_value_spacing=1, 
        minor_value_spacing=None):

    if major_index_spacing is not None:
        grid = PlotGrid(mapper=plot.index_mapper,
                orientation='horizontal', line_style='solid',
                line_color='lightgray',
                grid_interval=major_index_spacing)
        plot.underlays.append(grid)

    if minor_index_spacing is not None:
        grid = PlotGrid(mapper=plot.index_mapper,
                orientation='horizontal', line_style='dot',
                line_color='lightgray',
                grid_interval=minor_index_spacing)
        plot.underlays.append(grid)

    if major_value_spacing is not None:
        grid = PlotGrid(mapper=plot.value_mapper,
                orientation='vertical', line_style='solid',
                line_color='lightgray',
                grid_interval=major_value_spacing)
        plot.underlays.append(grid)

    if minor_value_spacing is not None:
        grid = PlotGrid(mapper=plot.value_mapper,
                orientation='vertical', line_style='dot',
                line_color='lightgray',
                grid_interval=minor_value_spacing)
        plot.underlays.append(grid)

class PositiveDTExperiment(AbstractPositiveExperiment):

    paradigm            = Instance(PositiveDTParadigm, ())
    #plot_data           = Instance(ArrayPlotData, ())
    plot_data           = Dict(Str, Instance(ArrayDataSource))
    plot_range          = Dict(Str, Instance(DataRange1D))
    color_legend        = List(Instance(ColorCategory), editor=legend_table)
    category_colors     = Dict()
    color_index         = Int(0)

    def _data_node_changed(self, new):
        self.data = PositiveDTData(store_node=new)

    def _update_data_categories(self, index_name, value_name, component):
        plot_name = index_name+value_name
        index = self.data.get_data(index_name)
        value = self.data.get_data(value_name)
        categories = [p[1:] for p in index]

        for category in sorted(set(categories)):
            mask = np.equal(categories, category)
            mask = np.flatnonzero(mask)
            category_index = np.take([p[0] for p in index], mask)
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

                index_range = self.plot_range[index_name]
                index_range.add(index_data)
                value_range = self.plot_range[value_name]
                value_range.add(value_data)

                if not category_name in self.category_colors:
                    c = COLOR_PALETTE[self.color_index]
                    self.category_colors[category_name] = c
                    self.color_index += 1

                index_mapper = LogMapper(range=index_range)
                value_mapper = LinearMapper(range=value_range)

                # Create the line plot
                overlay = OverlayPlotContainer()
                p = LinePlot(index=index_data, value=value_data,
                        index_mapper=index_mapper, value_mapper=value_mapper,
                        line_width=5)
                overlay.add(p)
                # Create the points for the line plot (i.e. scatter)
                p = ScatterPlot(index=index_data, value=value_data,
                        index_mapper=index_mapper, value_mapper=value_mapper,
                        marker='circle', outline_color='white', marker_size=8,
                        line_width=2)
                overlay.add(p)
                component.add(overlay)

                p.overlays.append(PlotAxis(p, orientation='left',
                    small_haxis_style=True, title=category_name))
                if len(component.components) == 1:
                    p.overlays.append(PlotAxis(p, orientation='bottom',
                        small_haxis_style=False))

    @on_trait_change('data.data_changed')
    def _update(self):
        self._update_data_categories('pars', 'par_go_count',
                self.par_count_plot)
        self._update_data_categories('pars', 'par_hit_frac',
                self.par_score_plot)
        self._update_data_categories('pars', 'par_dprime',
                self.par_dprime_plot)

    def _generate_summary_plots(self):
        container_kw = dict(padding=(50, 5, 5, 50), spacing=10,
                bgcolor='transparent')
        # COUNT
        container = VPlotContainer(**container_kw)
        index_range = DataRange1D()
        self.plot_range['pars'] = index_range
        value_range = DataRange1D(low_setting=0, high_setting='auto')
        self.plot_range['par_go_count'] = value_range
        self.par_count_plot = container

        # HIT RATE
        container = VPlotContainer(**container_kw)
        value_range = DataRange1D(low_setting=0, high_setting=1)
        self.plot_range['par_hit_frac'] = value_range
        self.par_score_plot = container

        # D'
        container = VPlotContainer(**container_kw)
        value_range = DataRange1D(low_setting=-1, high_setting=3)
        self.plot_range['par_dprime'] = value_range
        self.par_dprime_plot = container

    traits_view = View(
            HSplit(
                VGroup(
                    Item('handler.toolbar', style='custom'),
                    Include('status_group'),
                    Item('paradigm', style='custom', editor=InstanceEditor()),
                    Item('color_legend'),
                    show_labels=False,
                ),
                Include('plots_group'),
                Include('experiment_group'),
                show_labels=False,
                ),
            resizable=True,
            kind='live',
            handler=PositiveDTController)

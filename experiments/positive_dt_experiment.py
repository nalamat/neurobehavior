import numpy as np
from enthought.traits.api import Instance, Int, on_trait_change, \
        Dict, HasTraits, Any, List
from enthought.traits.ui.api import View, Include, VSplit, HSplit, \
        VGroup, Item, InstanceEditor

from abstract_positive_experiment import AbstractPositiveExperiment
from positive_dt_paradigm import PositiveDTParadigm
from positive_dt_controller import PositiveDTController

from positive_dt_data import PositiveDTData

from enthought.chaco.api import Plot, DataRange1D, LinearMapper, \
        PlotAxis, ArrayPlotData, Legend, LogMapper

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

class PositiveDTExperiment(AbstractPositiveExperiment):

    paradigm            = Instance(PositiveDTParadigm, ())
    plot_data           = Instance(ArrayPlotData, ())
    color_legend        = List(Instance(ColorCategory), editor=legend_table)
    category_colors     = Dict()
    color_index         = Int(0)

    def _data_node_changed(self, new):
        self.data = PositiveDTData(store_node=new)

    def _update_data_categories(self, index_name, value_name, plot):
        index = self.data.get_data(index_name)
        value = self.data.get_data(value_name)
        categories = [p[1:] for p in index]
        names = self.plot_data.list_data()

        for category in sorted(set(categories)):
            mask = np.equal(categories, category)
            mask = np.flatnonzero(mask)
            category_index = np.take([p[0] for p in index], mask)
            category_value = np.take(value, mask)
            if type(category) in (tuple, list):
                category_name = ', '.join([str(e) for e in category])
            else:
                category_name = str(category)
            self.plot_data.set_data(category_name+index_name, category_index)
            self.plot_data.set_data(category_name+value_name, category_value)
            if not category_name+value_name in names:
                # This is a new category.  Let's add the plot.  First, check to
                # see if we have already assigned a color to this category.
                if not category_name in self.category_colors:
                    c = COLOR_PALETTE[self.color_index]
                    self.category_colors[category_name] = c
                    self.color_index += 1

                color = self.category_colors[category_name] 

                xy = (category_name+index_name, category_name+value_name)
                plot.plot(xy, type='line', line_width=4, color=color)
                p, = plot.plot(xy, type='scatter', color=color, line_width=0)

                color_category = ColorCategory(label=category_name, color=color)
                if color_category not in self.color_legend:
                    self.color_legend.append(color_category)

    @on_trait_change('data.data_changed')
    def _update(self):
        self._update_data_categories('pars', 'par_go_count',
                self.par_count_plot)
        self._update_data_categories('pars', 'par_hit_frac',
                self.par_score_plot)
        self._update_data_categories('pars', 'par_dprime',
                self.par_dprime_plot)

    def _generate_summary_plots(self):
        plot = Plot(data=self.plot_data)

        #bounds = lambda low, high, margin, tight: (low-0.5, high+0.5)
        #index_range = DataRange1D(bounds_func=bounds)
        index_range = DataRange1D()
        bounds = lambda low, high, margin, tight: (0, high+1)
        value_range = DataRange1D(low_setting=0, high_setting='auto',
                bounds_func=bounds)
        plot.index_range = index_range
        plot.value_range = value_range
        #plot.index_mapper = LogMapper(range=index_range)
        #plot.value_mapper = LogMapper(range=value_range)

        axis = PlotAxis(plot, orientation='bottom')
        axis = PlotAxis(plot, orientation='bottom', title='Parameter')
        plot.underlays.append(axis)
        axis = PlotAxis(plot, orientation='left', title='Count')
        plot.underlays.append(axis)

        self.legend = Legend(resizable='')

        plot.overlays.append(self.legend)

        self.par_count_plot = plot

        # HIT rate
        plot = Plot(data=self.plot_data)

        #bounds = lambda low, high, margin, tight: (low-0.5, high+0.5)
        #index_range = DataRange1D(bounds_func=bounds)
        index_range = DataRange1D()
        value_range = DataRange1D(low_setting=0, high_setting=1)
        plot.index_range = index_range
        plot.value_range = value_range

        axis = PlotAxis(plot, orientation='bottom')
        axis = PlotAxis(plot, orientation='bottom', title='Parameter')
        plot.underlays.append(axis)
        axis = PlotAxis(plot, orientation='left', title='Hit rate (fraction)')
        plot.underlays.append(axis)

        self.par_score_plot = plot

        # D'
        plot = Plot(data=self.plot_data)

        #bounds = lambda low, high, margin, tight: (low-0.5, high+0.5)
        #index_range = DataRange1D(bounds_func=bounds)
        index_range = DataRange1D()
        value_range = DataRange1D(low_setting=-1, high_setting=3)
        plot.index_range = index_range
        plot.value_range = value_range

        axis = PlotAxis(plot, orientation='bottom')
        axis = PlotAxis(plot, orientation='bottom', title='Parameter')
        plot.underlays.append(axis)
        axis = PlotAxis(plot, orientation='left', title='Sensitivity (d\')')
        plot.underlays.append(axis)

        self.par_dprime_plot = plot

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

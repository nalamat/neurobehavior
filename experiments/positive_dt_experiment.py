import numpy as np
from enthought.traits.api import Instance, Int, on_trait_change, \
        Dict, HasTraits, Any, List, Str, Enum
from enthought.traits.ui.api import View, Include, VSplit, HSplit, \
        VGroup, Item, InstanceEditor

from abstract_positive_experiment import AbstractPositiveExperiment
from positive_dt_paradigm import PositiveDTParadigm
from positive_dt_controller import PositiveDTController

from positive_dt_data import PositiveDTData

from cns.chaco.helpers import add_default_grids

from enthought.chaco.api import Plot, DataRange1D, LinearMapper, \
        PlotAxis, ArrayPlotData, Legend, LogMapper, ArrayDataSource, \
        OverlayPlotContainer, LinePlot, ScatterPlot, BarPlot, \
        VPlotContainer
from enthought.chaco.tools.api import ScatterInspector, DataPrinter

from colors import paired_colors, paired_colors_255

class PositiveDTExperiment(AbstractPositiveExperiment):

    paradigm            = Instance(PositiveDTParadigm, ())
    plot_data           = Dict(Str, Instance(ArrayDataSource))
    plot_range          = Dict(Str, Instance(DataRange1D))
    color_index         = Int(0)
    color_map           = Dict

    group_mode          = Enum('overlay', 'stack')

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

                index_mapper = LogMapper(range=index_range)
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
                        axis = PlotAxis(p, orientation='left')
                        p.overlays.append(axis)
                        axis = PlotAxis(p, orientation='bottom')
                        p.overlays.append(axis)
                        if value_name == 'par_go_count':
                            add_default_grids(p, major_value=5, minor_value=1)
                        elif value_name == 'par_hit_frac':
                            add_default_grids(p, major_value=0.2,
                                    minor_value=0.05)
                        elif value_name == 'par_dprime':
                            add_default_grids(p, major_value=1,
                                    minor_value=0.25)

    @on_trait_change('data.trial_log')
    def _update(self):
        self._update_data_categories('pars', 'par_go_count',
                self.par_count_plot)
        self._update_data_categories('pars', 'par_hit_frac',
                self.par_score_plot)
        self._update_data_categories('pars', 'par_dprime',
                self.par_dprime_plot)

    @on_trait_change('data')
    def _generate_summary_plots(self):
        if self.group_mode == 'stack':
            container_class = VPlotContainer
        else:
            container_class = OverlayPlotContainer

        container_kw = dict(padding=(25, 5, 5, 25), spacing=10,
                            bgcolor='white')
        # COUNT
        container = container_class(**container_kw)
        index_range = DataRange1D()
        self.plot_range['pars'] = index_range
        value_range = DataRange1D(low_setting=0, high_setting='auto')
        self.plot_range['par_go_count'] = value_range
        self.par_count_plot = container

        # HIT RATE
        container = container_class(**container_kw)
        value_range = DataRange1D(low_setting=0, high_setting=1)
        self.plot_range['par_hit_frac'] = value_range
        self.par_score_plot = container

        # D'
        container = container_class(**container_kw)
        value_range = DataRange1D(low_setting=-1, high_setting=3)
        self.plot_range['par_dprime'] = value_range
        self.par_dprime_plot = container

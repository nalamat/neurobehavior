from numpy import clip

from enthought.traits.api import Instance, on_trait_change
from enthought.traits.ui.api import View, Item, VGroup, HGroup, HSplit, Tabbed
from enthought.enable.api import Component, ComponentEditor
from enthought.chaco.api import DataRange1D, LinearMapper, PlotLabel, \
        VPlotContainer, PlotAxis, PlotGrid, add_default_grids, \
        OverlayPlotContainer, Legend, ToolTip

from aversive_data import RawAversiveData as AversiveData
from aversive_data import AnalyzedAversiveData

from cns.chaco.channel_data_range import ChannelDataRange
from cns.chaco.channel_plot import ChannelPlot
from cns.chaco.ttl_plot import TTLPlot
from cns.chaco.dynamic_bar_plot import DynamicBarPlot, DynamicBarplotAxis

from abstract_experiment import AbstractExperiment
from abstract_aversive_paradigm import AbstractAversiveParadigm
from abstract_aversive_controller import AbstractAversiveController

import logging
log = logging.getLogger(__name__)

class AbstractAversiveExperiment(AbstractExperiment):

    data                = Instance(AversiveData)
    analyzed            = Instance(AnalyzedAversiveData)
    paradigm            = Instance(AbstractAversiveParadigm, ())

    experiment_plot     = Instance(Component)
    par_score_chart     = Instance(Component)
    score_chart         = Instance(Component)
    par_count_chart     = Instance(Component)
    par_dprime_chart    = Instance(Component)

    def _data_node_changed(self, new):
        self.data = AversiveData(store_node=new)
        self.analyzed = AnalyzedAversiveData(data=self.data)
        self._update_experiment_plot()
        self._update_score_chart()
        self._update_plots()

    def _update_experiment_plot(self):
        index_range = ChannelDataRange()
        index_range.sources = [self.data.contact_digital]
        index_mapper = LinearMapper(range=index_range)
        value_range = DataRange1D(low_setting=-0, high_setting=1)
        value_mapper = LinearMapper(range=value_range)

        container = OverlayPlotContainer(padding=50, spacing=50,
                fill_padding=True, bgcolor='white')

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

        # Add axes and grids to the first plot
        grid = PlotGrid(mapper=plot.index_mapper, component=plot,
                orientation='vertical', line_color='lightgray',
                line_style='dot', grid_interval=0.25)
        plot.underlays.append(grid)
        grid = PlotGrid(mapper=plot.index_mapper, component=plot,
                orientation='vertical', line_color='lightgray',
                line_style='solid', grid_interval=1)
        plot.underlays.append(grid)
        axis = PlotAxis(component=plot, title="Time (s)",
                        orientation="top", ticks_visible=True)
        plot.overlays.append(axis)
        tick_formatter = lambda s: "{0}:{1:02}".format(*divmod(int(s), 60))
        axis = PlotAxis(component=plot, orientation="bottom",
                title="Time(min:sec)",
                tick_label_formatter=tick_formatter)
        plot.underlays.append(axis)

        self.experiment_plot = container

    def _update_score_chart(self):
        preprocess = lambda x: clip(x, 0.2, 1.0)
        bounds = lambda low, high, margin, tight: (low-0.5, high+0.5)

        index_range = DataRange1D(low_setting='track', high_setting='auto',
                tracking_amount=75, bounds_func=bounds)
        value_range = DataRange1D(low_setting=0, high_setting=1)
        index_mapper = LinearMapper(range=index_range)
        value_mapper = LinearMapper(range=value_range)

        view = OverlayPlotContainer(bgcolor='white', fill_padding=True,
                padding=50)

        plot = DynamicBarPlot(source=self.analyzed,
                preprocess_values=preprocess,
                index_trait='remind_indices', value_trait='remind_seq',
                fill_color='lightgray', line_width=0.5, bar_width=1,
                index_mapper=index_mapper, value_mapper=value_mapper)

        axis = PlotAxis(component=plot, orientation='bottom',
                ticks_visible=True, title='Trial Number')
        plot.underlays.append(axis)
        label = PlotLabel(component=plot, text='On spout?')
        plot.underlays.append(label)
        index_range.add(plot.index)
        view.add(plot)

        plot = DynamicBarPlot(source=self.analyzed,
                preprocess_values=preprocess,
                index_trait='safe_indices', value_trait='fa_seq',
                fill_color=(0.41, 0.88, 0.25, 0.5), line_width=0.5, bar_width=1,
                index_mapper=index_mapper, value_mapper=value_mapper, alpha=0.5)
        index_range.add(plot.index)
        view.add(plot)

        plot = DynamicBarPlot(source=self.analyzed,
                preprocess_values=preprocess,
                index_trait='warn_indices', value_trait='hit_seq',
                fill_color='red', line_width=0.5, bar_width=1,
                index_mapper=index_mapper, value_mapper=value_mapper)
        index_range.add(plot.index)
        view.add(plot)

        self.score_chart = view

    def _update_plots(self):
        # dPrime
        bounds = lambda low, high, margin, tight: (low-0.5, high+0.5)
        index_range = DataRange1D(bounds_func=bounds)
        index_mapper = LinearMapper(range=index_range)
        value_range = DataRange1D(low_setting=-1, high_setting=4)
        value_mapper = LinearMapper(range=value_range)

        plot = DynamicBarPlot(source=self.analyzed,
                label_trait='pars', value_trait='par_dprime', bgcolor='white',
                padding=50, fill_padding=True, bar_width=0.9,
                value_mapper=value_mapper, index_mapper=index_mapper)
        index_range.add(plot.index)
        grid = PlotGrid(mapper=plot.value_mapper, component=plot,
                orientation='horizontal', line_color='lightgray',
                line_style='dot', grid_interval=1)
        plot.underlays.append(grid)
        axis = DynamicBarplotAxis(plot, orientation='bottom',
                source=self.analyzed, label_trait='pars', title='Parameter')
        plot.underlays.append(axis)
        plot.underlays.append(PlotAxis(plot, orientation='left', title="d'"))
        label = PlotLabel(component=plot, text="Sensitivity")
        plot.underlays.append(label)
        self.par_dprime_chart = plot

        # Trial count
        bounds = lambda low, high, margin, tight: (low-0.5, high+0.5)
        index_range = DataRange1D(bounds_func=bounds)
        index_mapper = LinearMapper(range=index_range)
        value_range = DataRange1D(low_setting=0, high_setting='auto')
        value_mapper = LinearMapper(range=value_range)

        plot = DynamicBarPlot(source=self.analyzed,
                label_trait='pars', value_trait='par_warn_count', bgcolor='white',
                padding=50, fill_padding=True, bar_width=0.9,
                value_mapper=value_mapper, index_mapper=index_mapper)
        index_range.add(plot.index)
        value_range.add(plot.value)
        grid = PlotGrid(mapper=plot.value_mapper, component=plot,
                orientation='horizontal', line_color='lightgray',
                line_style='dot', grid_interval=5)
        plot.underlays.append(grid)
        axis = DynamicBarplotAxis(plot, orientation='bottom',
                source=self.analyzed, label_trait='pars', title='Parameter')
        plot.underlays.append(axis)
        label = PlotLabel(component=plot, text="Trial Count")
        plot.underlays.append(label)
        plot.underlays.append(PlotAxis(plot, orientation='left'))
        self.par_count_chart = plot

        # par score chart
        bounds = lambda low, high, margin, tight: (low-0.8, high+0.8)
        index_range = DataRange1D(bounds_func=bounds)
        index_mapper = LinearMapper(range=index_range)
        value_range = DataRange1D(low_setting=0, high_setting=1)
        value_mapper = LinearMapper(range=value_range)

        chart = OverlayPlotContainer(bgcolor='white', fill_padding=True)

        plot = DynamicBarPlot(source=self.analyzed, label_trait='pars',
                value_trait='par_hit_frac', bgcolor='white', padding=50,
                fill_padding=True, bar_width=0.5, index_mapper=index_mapper,
                value_mapper=value_mapper, index_offset=-0.2, alpha=0.5)
        index_range.add(plot.index)

        axis = DynamicBarplotAxis(plot, orientation='bottom',
                source=self.analyzed, label_trait='pars', title='Parameter')
        plot.underlays.append(axis)
        axis = PlotAxis(plot, orientation='left', title='Fraction')
        plot.underlays.append(axis)
        label = PlotLabel(component=plot, text="FA (red) and Hit (black)")
        plot.underlays.append(label)
        
        grid = PlotGrid(mapper=plot.value_mapper, component=plot,
                orientation='horizontal', line_color='lightgray',
                line_style='dot', grid_interval=0.2)
        plot.underlays.append(grid)
        chart.add(plot)

        plot = DynamicBarPlot(source=self.analyzed, label_trait='pars',
                value_trait='par_fa_frac', bgcolor='white', padding=50,
                fill_padding=True, bar_width=0.5, fill_color=(1, 0, 0),
                index_mapper=index_mapper, value_mapper=value_mapper,
                index_offset=0.2, alpha=0.5)
        index_range.add(plot.index)
        chart.add(plot)
        self.par_score_chart = chart

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
                    Item('handler.current_volume_dispensed', 
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
                   VGroup(
                       Item('object.analyzed.mask_mode'),
                       Item('object.analyzed.include_last'), 
                       Item('object.analyzed.exclude_first'),
                       Item('object.analyzed.exclude_last'),
                       ),
                   ),
                show_labels=False,
                ),
            VGroup(
                Item('experiment_plot', editor=ComponentEditor(),
                    show_label=False, width=600, height=150),
                Item('score_chart', editor=ComponentEditor(),
                    show_label=False, width=600, height=150),
                HGroup(
                    Item('par_count_chart', show_label=False,
                        editor=ComponentEditor(), width=150, height=150),
                    Item('par_score_chart', editor=ComponentEditor(), width=150,
                        height=150, show_label=False),
                    Item('par_dprime_chart', editor=ComponentEditor(),
                        width=150, height=150, show_label=False),
                    ),
                ),
           show_labels=False,
           )
    
    traits_view = View(traits_group,
                       resizable=True,
                       kind='live',
                       handler=AbstractAversiveController)

if __name__ == "__main__":
    import tables
    store = tables.openFile('test.h5', 'w')
    # Will use the default paradigm

    if False:
        # This is an alternate way to load your experiment.  Rather than
        # subclassing AversiveExperiment (i.e. creating
        # AversiveMaskingExperiment) you could just provide the correct values).
        paradigm = AversiveMaskingParadigm()        # The masking paradigm
        controller = AversiveMaskingController()    # The masking controller
        experiment = AversiveExperiment(paradigm=paradigm, store_node=store.root)
        
        # Use configure_traits when launching program via command line.  edit_traits
        # is designed to work with interactive shells such as iPython.
        experiment.configure_traits(handler=controller)

        # When you call configure_traits (or edit_traits):
        # * GUI is created
        # * Controller (i.e. the handler) is created and hooked up to the GUI and
        # model (i.e. the experiment)
    else:
        # Log detailed information to file
        import logging
        from time import strftime
        filename = 'C:/experiments/logs/%s neurobehavior' % strftime('%Y%m%d_%H%M')
        file_handler = logging.FileHandler(filename)
        fmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(fmt)
        file_handler.setLevel(logging.DEBUG)
        logging.root.addHandler(file_handler)
        AversiveExperiment(store_node=store.root).configure_traits()

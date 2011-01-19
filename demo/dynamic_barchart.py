'''
Created on Apr 26, 2010

@author: Brad Buran
'''
import sys
sys.path.append('c:/experiments/programs/neurobehavior/branches/RZ6')

from enthought.chaco.api import PlotAxis
from cns.widgets.views.chart_view import DynamicBarPlotView, HistoryBarPlotView
from cns.chaco.dynamic_bar_plot import DynamicBarPlot, DynamicBarplotAxis
from enthought.pyface.timer.api import Timer
from enthought.traits.api import List, Array, on_trait_change, Instance, \
    HasTraits, Int, Button, Event
from enthought.traits.ui.api import View, HGroup, Handler, VGroup, Item
from numpy.random import random
from enthought.enable.component_editor import ComponentEditor

class DataHandler(Handler):

    timer = Instance(Timer)

    def init(self, info):
        self.timer = Timer(1e3, self.tick, info)

    def tick(self, info):
        n = len(info.object.parameters)
        data = random(n)
        info.object.fas = data
        info.object.fa_history.append(data.mean())
        info.object.updated = True

class Data(HasTraits):

    parameters = List([20, 10, 15, 40])
    fas = Array(dtype='f')

    fa_history = List()
    updated = Event

    parameter = Int
    add_parameter = Button

    dynamic_barchart = Instance(HasTraits)
    history_barchart = Instance(HasTraits)
    test_plot = Instance(DynamicBarPlot)

    def _test_plot_default(self):
        plot = DynamicBarPlot(source=self, bgcolor='white', value_trait='fas',
                padding=50, fill_padding=True, bar_width=0.9,
                label_trait='parameters',
                value_low_setting=0, value_high_setting=1)
        plot.underlays.append(DynamicBarplotAxis(plot, orientation='bottom'))
        return plot

    def _dynamic_barchart_default(self):
        r = DynamicBarPlotView(label='parameters',
                               value_trait='fas',
                               source=self,
                               bar_width=0.9,
                               value_min=0, value_max=1)
        return r

    def _history_barchart_default(self):
        return HistoryBarPlotView(value='fa_history',
                                  index_title='History',
                                  value_title='False Alarm Fraction',
                                  title='FA History',
                                  source=self,
                                  bar_width=0.9,
                                  value_min=0, value_max=1)

    @on_trait_change('add_parameter')
    def update_parameters(self):
        self.parameters.append(self.parameter)

    view = View(HGroup(VGroup(HGroup('parameter', 'add_parameter{}'),
                              Item('test_plot', editor=ComponentEditor(),
                                  height=200, width=200)),
                       #'history_barchart{}@',
                       ),
                height=250,
                width=500,
                handler=DataHandler(),
                resizable=True)

if __name__ == "__main__":
    Data().configure_traits()

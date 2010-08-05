'''
Created on Apr 26, 2010

@author: Brad Buran
'''

from cns.widgets.views.chart_view import DynamicBarPlotView, HistoryBarPlotView
from enthought.pyface.timer.api import Timer
from enthought.traits.api import List, Array, on_trait_change, Instance, \
    HasTraits, Int, Button, Event
from enthought.traits.ui.api import View, HGroup, Handler, VGroup
from numpy.random import random

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

    def _dynamic_barchart_default(self):
        r = DynamicBarPlotView(label='parameters',
                               value='fas',
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
                              'dynamic_barchart{}@'),
                       'history_barchart{}@',
                       ),
                height=250,
                width=500,
                handler=DataHandler(),
                resizable=True)

if __name__ == "__main__":
    Data().configure_traits()

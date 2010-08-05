'''
Created on Apr 26, 2010

@author: Brad Buran
'''

from cns.widgets.views.chart_view import HistoryBarPlotView
#from cns.widgets.views.component_view import BarChartOverlay
from cns.widgets.views.component_view import BarChartOverlay
from enthought.pyface.timer.api import Timer
from enthought.traits.api import List, Instance, \
    HasTraits, Int
from enthought.traits.ui.api import View, Item, Handler
from numpy.random import random
from numpy import clip

class DataHandler(Handler):

    timer = Instance(Timer)

    def init(self, info):
        self.timer = Timer(1e3, self.tick, info)

    def tick(self, info):
        '''This is basically a "dummy" function that pretends we're running a
        behavior experiment.  In this experiment, the probability of a correct
        rejection is 0.8 and the probability of a hit is 0.5.  This is a very
        contrived example: i.e. there's nothing preventing two WARN trials from
        occuring in sequence.
        '''
        info.object.curidx += 1
        if random() > 0.5:
            info.object.hit_history.append(random()>0.5)
            info.object.hit_history_indices.append(info.object.curidx)
        else:
            info.object.fa_history.append(random()>0.5)
            info.object.fa_history_indices.append(info.object.curidx)

class Data(HasTraits):

    # curidx is the total number of SAFE and WARN signals presented.  For
    # example:
    # SAFE SAFE SAFE WARN SAFE WARN SAFE SAFE WARN  <-- the sequence
    # 1    2    3    4    5    6    7    8    9     <-- curidx
    curidx = Int(0)
    fa_history = List()
    fa_history_indices = List()
    hit_history = List()
    hit_history_indices = List()

    # Defining the "plot" trait
    plot = Instance(BarChartOverlay)

    def _plot_default(self):
        # When you define a trait in a HasTraits class, you can specify the
        # default value for the trait by adding a method
        # _<traitname>_default(self) that returns the default value.  We utilize
        # this to generate the default value for the plot.

        # OverlayPlotContainer allows us to overlay multiple plots on top of
        # each other.  I use this to create two bar charts.  The first shows the
        # actual sequence of false alarms.  The second shows the sequence of
        # hits.  Note that this shows the *actual* sequence of SAFE and WARN
        # trials interleaved with each other.
        #
        # SAFE trials are light pink, WARN is red.  When the animal has a
        # correct reject or a miss, the bar is plotted at 0.2 so we have a
        # visual aid indicating whether that trial was a SAFE or WARN.
        preprocess = lambda x: clip(x, 0.2, 1.0)

        # I wrote the HistoryBarPlotView class to facilitate plotting sequences
        # of data.  The index (x-axis) is plotted as number of trials in the
        # past.
        template = HistoryBarPlotView(is_template=True,
                                      value_min=0,
                                      value_max=1,
                                      preprocess_values=preprocess)

        # The plot needs to know what the current index is so that it can
        # appropriately compute the "history": i.e. if the current index is 10,
        # it knows that a false alarm occuring at index 5 was 5 trials in the
        # past.  sync_trait ensures that everytime the 'curidx' trait of this
        # instance changes, the current_index trait on fa_plot is updated as
        # well.
        self.sync_trait('curidx', template, 'current_index')

        container = BarChartOverlay(template=template)
        c = container.add(index='fa_history_indices',
                      value='fa_history',
                      title='FA',
                      bar_color='lightpink',
                      bar_width=0.9,
                      source=self)
        print c.bar_color
        container.add(index='hit_history_indices',
                      value='hit_history',
                      source=self,
                      bar_width=0.9,
                      title='HIT',
                      bar_color='red')
        container.add_legend()
        return container

    view = View(Item('plot@', show_label=False),
                height=250,
                width=500,
                handler=DataHandler(),
                resizable=True)

if __name__ == "__main__":
    Data().configure_traits()
    #BarChartOverlay()
    #BarChartOverlay(template=HistoryBarPlotView())

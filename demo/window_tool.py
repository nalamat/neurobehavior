# Major library imports
from numpy import arange, sort
from numpy.random import random

from enthought.enable.example_support import DemoFrame, demo_main

# Enthought library imports
from enthought.enable.api import Component, ComponentEditor, Window
from enthought.traits.api import HasTraits, Instance, Button
from enthought.traits.ui.api import Item, Group, View

# Chaco imports
from enthought.chaco.api import ArrayPlotData, Plot
from cns.widgets.tools.window_tool import WindowTool

#===============================================================================
# # Create the Chaco plot.
#===============================================================================
def _create_plot_component():

    # Create some data
    numpts = 1000
    x = sort(random(numpts))
    y = random(numpts)

    # Create a plot data obect and give it this data
    pd = ArrayPlotData()
    pd.set_data("index", x)
    pd.set_data("value", y)

    # Create the plot
    plot = Plot(pd)
    plot.plot(("index", "value"),
              type="scatter",
              name="my_plot",
              marker="square",
              index_sort="ascending",
              color="lightblue",
              outline_color="none",
              marker_size=3,
              bgcolor="white")

    # Tweak some of the plot properties
    plot.title = "Click to add points, press Enter to finalize selection"
    plot.padding = 50
    plot.line_width = 1

    # Attach some tools to the plot
    #pan = PanTool(plot, drag_button="right", constrain_key="shift")
    #plot.tools.append(pan)
    #zoom = ZoomTool(component=plot, tool_mode="box", always_on=False)
    #plot.overlays.append(zoom)
    #plot.tools.append(WindowTool(plot))
    return plot

#===============================================================================
# Attributes to use for the plot view.
size=(650,650)
title="Line drawing example"
bg_color="lightgray"

#===============================================================================
# # Demo class that is used by the demo.py application.
#===============================================================================
class Demo(HasTraits):

    plot = Instance(Component)
    tool = Instance(WindowTool)
    show = Button('Show Windows')

    def _show_fired(self):
        print self.tool.coordinates
    
    traits_view = View(
                    Group(
                        Item('plot', editor=ComponentEditor(size=size),
                             show_label=False),
                        Item('show'),
                        orientation = "vertical"),
                    resizable=True, title=title
                    )
    
    def _plot_default(self):
        plot = _create_plot_component()
        self.tool = WindowTool(plot)
        plot.overlays.append(self.tool)
        return plot
    
demo = Demo()
demo.configure_traits()

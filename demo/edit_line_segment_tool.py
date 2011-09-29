#!/usr/bin/env python# Major library imports
from numpy import linspace
from scipy.special import jn

from enthought.enable.example_support import DemoFrame, demo_main
from enthought.chaco.example_support import COLOR_PALETTE

# Enthought library imports
#from enthought.enable.tools.api import DragTool
from cns.widgets.tools.line_edit_tool import LineEditTool
from enthought.enable.api import Component, ComponentEditor, Window
from enthought.traits.api import HasTraits, Instance, Int, Tuple
from enthought.traits.ui.api import Item, Group, View

# Chaco imports
from enthought.chaco.api import add_default_axes, add_default_grids, \
        OverlayPlotContainer, PlotLabel, ScatterPlot, create_line_plot
from enthought.chaco.tools.api import PanTool, ZoomTool

#===============================================================================
# # Create the Chaco plot.
#===============================================================================
def _create_plot_component():
    
    container = OverlayPlotContainer(padding = 50, fill_padding = True,
                                     bgcolor = "lightgray", use_backbuffer=True)

    # Create the initial X-series of data
    numpoints = 5
    low = -5
    high = 15.0
    x = linspace(low, high, numpoints)
    y = jn(0, x)

    lineplot = create_line_plot((x,y), color=tuple(COLOR_PALETTE[0]), width=2.0)
    lineplot.selected_color = "none"
    scatter = ScatterPlot(index = lineplot.index,
                       value = lineplot.value,
                       index_mapper = lineplot.index_mapper,
                       value_mapper = lineplot.value_mapper,
                       color = tuple(COLOR_PALETTE[0]),
                       marker_size = 5)
    scatter.index.sort_order = "ascending"

    scatter.bgcolor = "white"
    scatter.border_visible = True
    
    add_default_grids(scatter)
    add_default_axes(scatter)

    scatter.tools.append(PanTool(scatter, drag_button="right"))
    
    # The ZoomTool tool is stateful and allows drawing a zoom
    # box to select a zoom region.
    zoom = ZoomTool(scatter, tool_mode="box", always_on=False, drag_button=None)
    scatter.overlays.append(zoom)

    scatter.tools.append(LineEditTool(scatter, drag_mode='Y', monotonic=True))

    container.add(lineplot)
    container.add(scatter)

    # Add the title at the top
    container.overlays.append(PlotLabel("Line Editor",
                              component=container,
                              font = "swiss 16",
                              overlay_position="top"))
    
    return container


#===============================================================================
# Attributes to use for the plot view.
size=(800,700)
title="Simple line plot"
#===============================================================================
# # Demo class that is used by the demo.py application.
#===============================================================================
class Demo(HasTraits):
    plot = Instance(Component)
    
    traits_view = View(
                    Group(
                        Item('plot', editor=ComponentEditor(size=size), 
                             show_label=False),
                        orientation = "vertical"),
                    resizable=True, title=title
                    )
    
    def _plot_default(self):
         return _create_plot_component()
    
demo = Demo()

#===============================================================================
# Stand-alone frame to display the plot.
#===============================================================================
class PlotFrame(DemoFrame):

    def _create_window(self):
        # Return a window containing our plots
        return Window(self, -1, component=_create_plot_component())
    
if __name__ == "__main__":
    demo_main(PlotFrame, size=size, title=title)

#--EOF---


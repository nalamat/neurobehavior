#!/usr/bin/env python
"""
Draws some different polygons
 - Left-drag pans the plot.
 - Mousewheel up and down zooms the plot in and out.
 - Pressing "z" brings up the Zoom Box, and you can click-drag a rectangular 
   region to zoom.  If you use a sequence of zoom boxes, pressing alt-left-arrow
   and alt-right-arrow moves you forwards and backwards through the "zoom 
   history".
"""

# Major library imports
import math
from numpy import array, transpose
import numpy as np

from enthought.enable.example_support import DemoFrame, demo_main

# Enthought library imports
from enthought.enable.api import Component, ComponentEditor, Window
from enthought.traits.api import HasTraits, Instance, Enum, Tuple, Dict
from enthought.traits.ui.api import Item, Group, View

# Chaco imports
from enthought.chaco.api import ArrayPlotData, HPlotContainer, Plot
from enthought.chaco.base import n_gon
from enthought.chaco.tools.api import PanTool, ZoomTool, DragTool


def _create_plot_component():

    # Use n_gon to compute center locations for our polygons
    points = n_gon(center=(0,0), r=4, nsides=8)
 
    # Choose some colors for our polygons
    colors = {3:'red',   4:'orange', 5:'yellow',    6:'lightgreen',
              7:'green', 8:'blue',   9:'lavender', 10:'purple'}
 
    # Create a PlotData object to store the polygon data
    pd = ArrayPlotData()

    # Create a Polygon Plot to draw the regular polygons
    polyplot = Plot(pd)

    # Store path data for each polygon, and plot

    pd.set_data("x", np.r_[np.arange(12), np.arange(12)[::-1]])
    pd.set_data("y", np.r_[np.abs(np.random.randn(12)),
        -2*np.abs(np.random.randn(12))])

    polyplot.plot(("x", "y"), type='polygon', face_color='black')

    # Tweak some of the plot properties
    polyplot.padding = 50
    polyplot.title = "My First Polygon Plot"

    # Attach some tools to the plot
    #polyplot.tools.append(PanTool(polyplot))
    #zoom = ZoomTool(polyplot, tool_mode="box", always_on=False)
    #polyplot.overlays.append(zoom)
    return polyplot

#===============================================================================
# Attributes to use for the plot view.
size=(800,800)
title="Basic Polygon Plot"

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

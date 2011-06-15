import numpy as np
from enthought.enable.api import MarkerTrait, ColorTrait
from enthought.chaco.api import AbstractOverlay
from enthought.chaco.scatterplot import render_markers
from enthought.traits.api import Instance, Any, Property, cached_property, Int, Float, List
from enthought.traits.ui.api import View, VGroup, Item

class ThresholdOverlay(AbstractOverlay):

    plot = Instance('enthought.enable.api.Component')
    #spikes = Any

    line_width = Int(2)
    line_color = ColorTrait('red')
    
    thresholds = List(Float)
    _th_screen = Property(depends_on='thresholds, plot.channel_visible')
    
    def _get__th_screen(self):
        bounds = []
        for o, ch in zip(self.plot.offsets, self.plot.channel_visible):
            lb = self.plot.value_mapper.map_screen(o+self.thresholds[ch])
            ub = self.plot.value_mapper.map_screen(o-self.thresholds[ch])
            bounds.append((lb, ub))
        return bounds
    
    def overlay(self, component, gc, view_bounds=None, mode="normal"):
        if len(self.plot.channel_visible) != 0:
            with gc:
                gc.clip_to_rect(component.x, component.y, component.width,
                                component.height)
                gc.set_line_width(self.line_width)
                gc.set_stroke_color(self.line_color_)
                
                for ylb, yub in self._th_screen:
                    xlb = component.x
                    xub = component.x+component.width
                    gc.move_to(xlb, ylb)
                    gc.line_to(xub, ylb)
                    gc.move_to(xlb, yub)
                    gc.line_to(xub, yub)

                gc.stroke_path()                
                
    traits_view = View(
        VGroup(
            Item('line_color'),
            Item('line_width'),
            show_border=True,
            label='Threshold overlay',
            )            
        )
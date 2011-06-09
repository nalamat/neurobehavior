import numpy as np
from enthought.enable.api import MarkerTrait, ColorTrait
from enthought.chaco.api import AbstractOverlay
from enthought.chaco.scatterplot import render_markers
from enthought.traits.api import Instance, Any, Property, cached_property, Int, Float

class ThresholdOverlay(AbstractOverlay):

    plot = Instance('enthought.enable.api.Component')
    spikes = Any

    line_width = Int(2)
    line_color = ColorTrait('red')
    
    threshold = Float(0.0001)
    
    @cached_property
    def _get_spike_screen_offsets(self):
        spike_offsets = self.plot.offsets
        return self.plot.value_mapper.map_screen(spike_offsets)

    def overlay(self, component, gc, view_bounds=None, mode="normal"):
        if len(self.plot.channel_visible) != 0:
            with gc:
                gc.clip_to_rect(component.x, component.y, component.width,
                                component.height)
                gc.set_line_width(self.line_width)
                gc.set_stroke_color(self.line_color_)
                
                for o in self.plot.offsets:
                    yub, = self.plot.value_mapper.map_screen(o+self.threshold)
                    ylb, = self.plot.value_mapper.map_screen(o-self.threshold)
                    
                    xlb = component.x
                    xub = component.x+component.width
                    
                    gc.move_to(xlb, ylb)
                    gc.line_to(xub, ylb)
                    gc.move_to(xlb, yub)
                    gc.line_to(xub, yub)

                gc.stroke_path()
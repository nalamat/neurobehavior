from __future__ import division

import numpy as np
from extremes_channel_plot import ExtremesChannelPlot
from enthought.traits.api import List, Float, Property, cached_property

class ExtremesMultiChannelPlot(ExtremesChannelPlot):
    
    # Offset of all channels along the value axis
    channel_offset  = Float(0.25e-3)
    # Distance between each channel along the value axis
    channel_spacing = Float(0.5e-3)
    # Which channels are visible?
    channel_visible = List([])

    offsets = Property(depends_on='channel_+, value_mapper.updated')
    screen_offsets = Property(depends_on='offsets')

    def _offset_changed(self):
        self._invalidate_screen()

    def _visible_changed(self):
        self._invalidate_screen()

    def _spacing_changed(self):
        self._invalidate_screen()

    @cached_property
    def _get_offsets(self):
        channels = len(self.channel_visible)
        offsets = self.channel_spacing*np.arange(channels)[:,np.newaxis]
        return offsets[::-1] + self.channel_offset

    @cached_property
    def _get_screen_offsets(self):
        return self.value_mapper.map_screen(self.offsets)

    def _map_screen(self, data):
        spaced_data = data[self.channel_visible] + self.offsets
        return self.value_mapper.map_screen(spaced_data)

    def _render(self, gc, points):
        if len(points[0]) == 0:
            return

        gc.save_state()
        gc.clip_to_rect(self.x, self.y, self.width, self.height)
        gc.set_stroke_color(self.line_color_)
        gc.set_line_width(self.line_width) 

        gc.begin_path()
        if self.draw_mode == 'normal':
            idx, val = points
            for v in val:
                gc.lines(np.c_[idx, v])
        else:
            idx, (mins, maxes) = points
            for lb, ub in zip(mins, maxes):
                starts = np.column_stack((idx, lb))
                ends = np.column_stack((idx, ub))
                gc.line_set(starts, ends)

        gc.stroke_path()
        self._draw_default_axes(gc)
        gc.restore_state()

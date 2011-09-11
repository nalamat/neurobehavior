import numpy as np

#from enthought.chaco.api import BaseXYPlot
from .channel_plot import ChannelPlot
from enthought.enable.api import black_color_trait, LineStyle, MarkerTrait
from enthought.traits.api import Instance, Float, Event, Bool, Enum, \
        on_trait_change, Str

class EpochPlot(ChannelPlot):
    '''
    Designed for efficiently handling time series data stored in a channel.
    Each time a Channel.updated event is fired, the new data is obtained and
    plotted.
    '''

    series              = Instance('cns.channel.Epoch')
    marker              = MarkerTrait
    marker_size         = Float(4.0)
    marker_color        = black_color_trait
    marker_edge_color   = black_color_trait
    marker_edge_width   = Float(1.0)
    marker_height       = Float(0.5)
    line_color          = black_color_trait
    line_style          = LineStyle

    def _gather_points(self):
        if not self._data_cache_valid:
            range = self.index_mapper.range
            self._cached_data = self.series.get_range(range.low, range.high)
            self._data_cache_valid = True
            self._screen_cache_valid = False

    def _get_screen_points(self):
        if not self._screen_cache_valid:
            screen_index = self.index_mapper.map_screen(self._cached_data)
            screen_position = self.value_mapper.map_screen(self.marker_height)
            screen_value = np.ones(len(screen_index))*screen_position
            self._cached_screen_points = np.c_[screen_index, screen_value]
            self._screen_cache_valid = True
        return self._cached_screen_points

    def _render(self, gc, points):
        if len(points) == 0:
            return

        gc.save_state()
        gc.set_antialias(True)
        gc.clip_to_rect(self.x, self.y, self.width, self.height)

        gc.set_fill_color(self.marker_color_)
        gc.set_stroke_color(self.marker_edge_color_)
        gc.set_line_width(self.marker_edge_width) 
        gc.set_line_join(0) # Curved

        starts = points[:,(0,2)]
        ends = points[:,(1,2)]

        gc.line_set(starts, ends)
        gc.stroke_path()
        gc.draw_marker_at_points(starts, self.marker_size,
                self.marker_.kiva_marker)
        gc.draw_marker_at_points(ends, self.marker_size,
                self.marker_.kiva_marker)

        self._draw_default_axes(gc)
        gc.restore_state()

    def _data_changed(self, timestamps):
        # Only fire an update if the changed data is within bounds
        if self.index_range.mask_data(np.array(timestamps)).any():
            self.invalidate_draw()
            self._data_cache_valid = False
            self.request_redraw()

    def _series_changed(self, old, new):
        if old is not None:
            old.on_trait_change(self._data_changed, "updated", remove=True)
        if new is not None:
            new.on_trait_change(self._data_changed, "updated", dispatch="new")

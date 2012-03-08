from __future__ import division

from base_channel_plot import BaseChannelPlot
import numpy as np
from enthought.traits.api import Bool, Property, cached_property, Int

class ChannelPlot(BaseChannelPlot):
    '''
    Designed for efficiently handling time series data stored in a channel.
    Each time a Channel.updated event is fired, the new data is obtained and
    plotted.
    '''
    _data_cache_valid       = Bool(False)
    _screen_cache_valid     = Bool(False)

    # When decimating, how many samples should be extracted per pixel?
    dec_points = Int(2)
    dec_factor = Property(depends_on='index_mapper.updated, dec_points, source.fs')

    def _invalidate_data(self):
        self._data_cache_valid = False
        self.invalidate_and_redraw()

    def _invalidate_screen(self):
        self._screen_cache_valid = False
        self.invalidate_and_redraw()

    def __init__(self, **kwargs):
        super(ChannelPlot, self).__init__(**kwargs)
        self._index_mapper_changed(None, self.index_mapper)

    def _index_mapper_updated(self):
        '''
        Compute array of index values (i.e. the time of each sample that could
        be displayed in the visible range)
        '''
        if self.source is not None:
            fs = self.source.fs
            # Channels contain continuous data starting at t0.  We do not want
            # to compute time values less than t0.
            if self.index_range.low > self.source.t0:
                low = int(self.index_range.low*fs)
            else:
                low = int(self.source.t0*fs)
            high = int(self.index_range.high*fs)
            self.index_values = np.arange(low, high)/fs
            self._data_cache_valid = False
            self._invalidate_screen()

    def _index_mapper_changed(self, old, new):
        if old is not None:
            old.on_trait_change(self._index_mapper_updated, "updated",
                    remove=True)
        if new is not None:
            new.on_trait_change(self._index_mapper_updated, "updated")

    @cached_property
    def _get_dec_factor(self):
        '''
        Compute decimation factor based on the sampling frequency of the channel
        itself.
        '''
        screen_min, screen_max = self.index_mapper.screen_bounds
        screen_width = screen_max-screen_min # in pixels
        range = self.index_range
        data_width = (range.high-range.low)*self.source.fs
        return np.floor((data_width/screen_width)/self.dec_points)

    def _preprocess_data(self, data):
        return data

    def _gather_points(self):
        if not self._data_cache_valid:
            range = self.index_mapper.range
            data = self.source.get_range(range.low, range.high)
            self._cached_data = self._preprocess_data(data)
            self._data_cache_valid = True
            self._screen_cache_valid = False

    def _get_screen_points(self):
        if not self._screen_cache_valid:
            # Obtain cached data and map to screen
            val_pts = self._cached_data
            s_val_pts = self._map_screen(val_pts) 
            self._cached_screen_data = s_val_pts

            # Obtain cached data bounds and create index points
            #n = len(val_pts)
            n = val_pts.shape[-1]
            t_screen = self.index_mapper.map_screen(self.index_values[:n])
            self._cached_screen_index = t_screen

            # Screen cache is valid
            self._screen_cache_valid = True
            
        return self._cached_screen_index, self._cached_screen_data

    def _map_screen(self, data):
        return self.value_mapper.map_screen(data)

    def _draw_plot(self, gc, view_bounds=None, mode="normal"):
        self._gather_points()
        points = self._get_screen_points()
        self._render(gc, points)

    def _render(self, gc, points):
        idx, val = points
        if len(idx) == 0:
            return
        gc.save_state()
        gc.set_antialias(True)
        gc.clip_to_rect(self.x, self.y, self.width, self.height)
        gc.set_stroke_color(self.line_color_)
        gc.set_line_width(self.line_width) 
        gc.begin_path()
        gc.lines(np.column_stack((idx, val)))
        gc.stroke_path()
        self._draw_default_axes(gc)
        gc.restore_state()


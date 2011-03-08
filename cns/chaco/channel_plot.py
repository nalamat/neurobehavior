import numpy as np

from enthought.chaco.api import BaseXYPlot
from enthought.enable.api import black_color_trait, LineStyle
from enthought.traits.api import Instance, Float, Event, Bool, Enum, \
        on_trait_change, Property

class ChannelPlot(BaseXYPlot):
    '''
    Designed for efficiently handling time series data stored in a channel.
    Each time a Channel.updated event is fired, the new data is obtained and
    plotted.
    '''

    channel                 = Instance('cns.channel.Channel')
    fill_color              = black_color_trait
    line_color              = black_color_trait
    line_width              = Float(1.0)
    line_style              = LineStyle
    reference               = Float(-1.0)
    data_changed            = Event
    _data_cache_valid       = Bool(False)
    _screen_cache_valid     = Bool(False)

    index                   = Property(depends_on='channel')

    def _get_index(self):
        return self.channel

    def __init__(self, **kwargs):
        super(ChannelPlot, self).__init__(**kwargs)
        self.index_mapper.on_trait_change(self._index_range_updated, "updated")

    def _index_range_updated(self):
        '''
        Compute array of index values (i.e. the time of each sample that could
        be displayed in the visible range)
        '''
        if self.channel is not None:
            fs = self.channel.fs
            # Channels contain continuous data starting at t0.  We do not want
            # to compute time values less than t0.
            if self.index_range.low > self.channel.t0:
                low = int(self.index_range.low*fs)
            else:
                low = int(self.channel.t0*fs)
            high = int(self.index_range.high*fs)
            self.index_values = np.arange(low, high)/fs

    def _index_mapper_changed(self, old, new):
        super(ChannelPlot, self)._index_mapper_changed(old, new)
        old.on_trait_change(self._index_range_updated, "updated", remove=True)
        new.on_trait_change(self._index_range_updated, "updated", remove=True)

    def _decimation_factor(self):
        '''
        Compute decimation factor based on the sampling frequency of the channel
        itself.
        '''
        screen_min, screen_max = self.index_mapper.screen_bounds
        screen_width = screen_max-screen_min # in pixels
        range = self.index_range
        data_width = (range.high-range.low)*self.channel.fs
        return np.floor((data_width/screen_width))

    def _gather_points(self):
        if not self._data_cache_valid:
            range = self.index_mapper.range
            self._cached_data = self.channel.get_range(range.low, range.high)
            self._data_cache_valid = True
            self._screen_cache_valid = False

    def _get_screen_points(self):
        if not self._screen_cache_valid:
            # Obtain cached data and map to screen
            val_pts = self._cached_data
            s_val_pts = self.value_mapper.map_screen(val_pts) 
            self._cached_screen_data = s_val_pts

            # Obtain cached data bounds and create index points
            n = len(val_pts)
            t_screen = self.index_mapper.map_screen(self.index_values[:n])
            self._cached_screen_index = t_screen

            # Screen cache is valid
            self._screen_cache_valid = True
            
        return self._cached_screen_index, self._cached_screen_data

    def _draw_plot(self, gc, view_bounds=None, mode="normal"):
        self._gather_points()
        points = self._get_screen_points()
        self._render(gc, points)

    def _render(self, gc, points):
        try:
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
        except ValueError, e:
            print len(idx), len(val)

    def _data_changed(self):
        self.invalidate_draw()
        self._data_cache_valid = False
        self.request_redraw()

    def _channel_changed(self, old, new):
        if old is not None:
            old.on_trait_change(self._data_changed, "updated", remove=True)
        if new is not None:
            new.on_trait_change(self._data_changed, "updated", dispatch="new")

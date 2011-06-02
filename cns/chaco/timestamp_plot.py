import numpy as np

from enthought.chaco.api import BaseXYPlot
from enthought.enable.api import black_color_trait, LineStyle
from enthought.traits.api import Instance, Float, Event, Bool, Enum, \
        on_trait_change

class TimeseriesPlot(BaseXYPlot):
    '''
    Designed for efficiently handling time series data stored in a channel.
    Each time a Channel.updated event is fired, the new data is obtained and
    plotted.
    '''

    series                  = Instance('cns.channel.Timeseries')
    fill_color              = black_color_trait
    line_color              = black_color_trait
    line_width              = Float(1.0)
    line_style              = LineStyle
    reference               = Float(-1.0)
    data_changed            = Event
    _data_cache_valid       = Bool(False)
    _screen_cache_valid     = Bool(False)
    rect_height             = Float(0.5)
    rect_center             = Float(0.5)

    #def __init__(self, **kwargs):
    #    super(TimeseriesPlot, self).__init__(**kwargs)
    #    self.index_mapper.on_trait_change(self._index_range_updated, "updated")

    #def _index_range_updated(self):
    #    '''
    #    Compute array of index values (i.e. the time of each sample that could
    #    be displayed in the visible range)
    #    '''
    #    if self.series is not None:
    #        fs = self.series.fs
    #        # Channels contain continuous data starting at t0.  We do not want
    #        # to compute time values less than t0.
    #        if self.index_range.low > self.series.t0:
    #            low = int(self.index_range.low*fs)
    #        else:
    #            low = int(self.channel.t0*fs)
    #        high = int(self.index_range.high*fs)
    #        self.index_values = np.arange(low, high)/fs

    def _index_mapper_changed(self, old, new):
        super(ChannelPlot, self)._index_mapper_changed(old, new)
        old.on_trait_change(self._index_range_updated, "updated", remove=True)
        new.on_trait_change(self._index_range_updated, "updated", remove=True)

    #def _decimation_factor(self):
    #    '''
    #    Compute decimation factor based on the sampling frequency of the channel
    #    itself.
    #    '''
    #    screen_min, screen_max = self.index_mapper.screen_bounds
    #    screen_width = screen_max-screen_min # in pixels
    #    range = self.index_range
    #    data_width = (range.high-range.low)*self.channel.fs
    #    return np.floor((data_width/screen_width))

    def _gather_points(self):
        if not self._data_cache_valid:
            range = self.index_mapper.range
            data = np.array(self.series.buffer)
            mask = (data>=range.low) & (data<range.high)
            self._cached_data = data[mask]
            self._data_cache_valid = True
            self._screen_cache_valid = False

    def _get_screen_points(self):
        if not self._screen_cache_valid:
            # Obtain cached data bounds and create index points
            t_screen = self.index_mapper.map_screen(self._cached_data)
            self._cached_screen_index = t_screen
            # Screen cache is valid
            self._screen_cache_valid = True
            
        return self._cached_screen_index

    def _draw_plot(self, gc, view_bounds=None, mode="normal"):
        self._gather_points()
        points = self._get_screen_points()
        self._render(gc, points)

    def _render(self, gc, points):
        lines = points
        if len(lines) == 0:
            return

        low = self.rect_center-self.rect_height*0.5
        high = self.rect_center+self.rect_height*0.5
        screen_low = self.value_mapper.map_screen(high)
        screen_high = self.value_mapper.map_screen(low)
        screen_height = screen_high-screen_low

        starts = lines, np.ones(n)*screen_low
        ends = lines, np.ones(n)*screen_height

        gc.save_state()
        try:
            gc.set_antialias(True)
            gc.clip_to_rect(self.x, self.y, self.width, self.height)

            # Set up appearance
            gc.set_stroke_color(self.line_color_)
            #gc.set_fill_color(self.fill_color_)
            gc.set_line_width(self.line_width) 
            gc.set_line_dash(self.line_style_)
            gc.set_line_join(0) # Curved

            gc.begin_path()
            #gc.rects(np.column_stack((x, y, width, height)))
            gc.line_set(starts, ends)
            gc.draw_path()

            self._draw_default_axes(gc)
        finally:
            gc.restore_state()

    def _data_changed(self):
        self.invalidate_draw()
        self._data_cache_valid = False
        self.request_redraw()

    def _channel_changed(self, old, new):
        if old is not None:
            old.on_trait_change(self._data_changed, "updated", remove=True)
        if new is not None:
            new.on_trait_change(self._data_changed, "updated", dispatch="new")

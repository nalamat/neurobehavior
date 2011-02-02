import numpy as np

from enthought import kiva
from enthought.chaco.api import BaseXYPlot
from enthought.enable.api import black_color_trait, LineStyle
from enthought.traits.api import Instance, Float, Event, Bool, Enum, \
        on_trait_change, Str

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
    label                   = Str("Timeseries")
    text_rotation           = Float(np.pi/4)

    def _gather_points(self):
        if not self._data_cache_valid:
            range = self.index_mapper.range
            self._cached_data = self.series.get_range(range.low, range.high)
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
        n = len(lines)
        if n == 0:
            return

        low = self.rect_center-self.rect_height*0.5
        high = self.rect_center+self.rect_height*0.5
        screen_low = self.value_mapper.map_screen(high)
        screen_high = self.value_mapper.map_screen(low)

        starts = np.column_stack((lines, np.ones(n)*screen_low))
        ends = np.column_stack((lines, np.ones(n)*screen_high))

        gc.save_state()
        try:
            gc.set_antialias(True)
            gc.clip_to_rect(self.x, self.y, self.width, self.height)

            # Set up appearance
            gc.set_stroke_color(self.line_color_)
            gc.set_fill_color(self.fill_color_)
            gc.set_line_width(self.line_width) 
            gc.set_line_dash(self.line_style_)
            gc.set_line_join(0) # Curved
            gc.set_font(kiva.Font())

            gc.begin_path()
            gc.line_set(starts, ends)
            gc.rotate_ctm(self.text_rotation)
            for i, (x, y) in enumerate(starts):
                gc.set_text_position(x, y)
                try:
                    gc.show_text(self.label + "%r" % self.series.metadata[i])
                except:
                    gc.show_text(self.label)
                gc.draw_marker_at_points([[x, y]], 1, 1)
            gc.draw_path()
            self._draw_default_axes(gc)
        finally:
            gc.restore_state()

    def _data_changed(self):
        self.invalidate_draw()
        self._data_cache_valid = False
        self.request_redraw()

    def _series_changed(self, old, new):
        if old is not None:
            old.on_trait_change(self._data_changed, "updated", remove=True)
        if new is not None:
            new.on_trait_change(self._data_changed, "updated", dispatch="new")

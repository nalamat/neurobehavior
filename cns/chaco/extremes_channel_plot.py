import numpy as np
from channel_plot import ChannelPlot
from enthought.traits.api import List, Float, on_trait_change
from enthought.kiva import fonttools

import logging
log = logging.getLogger(__name__)

def decimate_extremes(data, downsample):
    # Axis that we want to decimate across
    if data.shape[-1] == 0:
        return [], []

    last_dim = data.ndim
    offset = data.shape[-1] % downsample

    # Force a copy to be made, which speeds up min()/max().  Apparently min/max
    # make a copy of a reshaped array before performing the operation, so we
    # force it now so the copy only occurs once.
    if data.ndim == 2:
        shape = (len(data), -1, downsample)
    else:
        shape = (-1, downsample)
    data = data[..., :-offset].reshape(shape).copy()
    return data.min(last_dim), data.max(last_dim)

class ExtremesChannelPlot(ChannelPlot):
    '''
    Often our neurophysiology data involves sampling at up to 200kHz.  If we are
    viewing a second's worth of data on screen using standard plotting
    functions, then this means we are computing the data to screen coordinate
    transform of 200,000 points every few milliseconds and then blitting this to
    screen.

    Instead, each time a new call to render the plot on screen is made (e.g.
    there's new data, the screen is resized, or the data bounds change), the
    data is downsampled so there is only one vertical "line" per screen pixel.
    The line runs from the minimum to the maximum.  This is great for plotting
    neurophysiology data since you can see the noise floor and individual spikes
    will show up quite well.

    In cases where there are fewer data points than screen pixels, then the plot
    reverts to a standard "connected" XY plot.
    '''

    # Offset of all channels along the value axis
    channel_offset  = Float(0.25e-3)

    # Distance between each channel along the value axis
    channel_spacing = Float(0.5e-3)

    # Which channels are visible?
    channel_visible = List([])

    # Offset, spacing and visible only affect the screen points, so we only
    # invalidate the screen cache.  The data cache is fine.

    def _invalidate_screen(self):
        self.invalidate_draw()
        self._screen_cache_valid = False
        self.request_redraw()

    def _offset_changed(self):
        self._invalidate_screen()

    def _visible_changed(self):
        self._invalidate_screen()

    def _spacing_changed(self):
        self._invalidate_screen()

    def _get_screen_points(self):
        if not self._screen_cache_valid:
            if self._cached_data.shape[-1] == 0:
                self._cached_screen_index = []
                self._cached_screen_data = []
            else:
                if len(self.channel_visible) == 0:
                    self._cached_screen_data = []
                    self._cached_screen_index = []
                    self._screen_cache_valid = True
                    return self._cached_screen_index, self._cached_screen_data
                    
                # Get the decimated data
                decimation_factor = self._decimation_factor()
                cached_data = self._cached_data[self.channel_visible]
                values = decimate_extremes(cached_data, decimation_factor)

                channels = len(self.channel_visible)
                offsets = self.channel_spacing*np.arange(channels)[:,np.newaxis]
                offsets = offsets[::-1] + self.channel_offset

                text_offsets = offsets+self.channel_spacing/3.0
                self._cached_offsets = self.value_mapper.map_screen(text_offsets)

                if type(values) == type(()):
                    channels, samples = values[0].shape

                    mins = values[0] + offsets
                    s_val_min = self.value_mapper.map_screen(mins)

                    maxes = values[1] + offsets
                    s_val_max = self.value_mapper.map_screen(maxes)
                    self._cached_screen_data = s_val_min, s_val_max
                else:
                    channels, samples = values.shape
                    s_val_pts = self.value_mapper.map_screen(values)
                    s_val_pts = s_val_pts/channels + offsets
                    self._cached_screen_data = s_val_pts

                total_samples = self._cached_data.shape[-1]
                t = self.index_values[:total_samples:decimation_factor][:samples]
                t_screen = self.index_mapper.map_screen(t)
                self._cached_screen_index = t_screen
                self._screen_cache_valid = True

        return self._cached_screen_index, self._cached_screen_data

    def _render_channel_numbers(self, gc):
        gc.set_font(fonttools.Font(size=24, weight=10))
        #x = self._cached_screen_index[0]
        x = 0
        gc.set_fill_color((1.0, 0.0, 0.0, 1.0))
        for offset, number in zip(self._cached_offsets, self.channel_visible):
            gc.set_text_position(int(x), int(offset))
            gc.show_text(str(number+1))

    def _render(self, gc, points):
        idx, val = points
        if len(idx) == 0:
            return

        gc.save_state()
        gc.clip_to_rect(self.x, self.y, self.width, self.height)
        gc.set_stroke_color(self.line_color_)
        gc.set_line_width(self.line_width) 

        gc.begin_path()
        if type(val) == type(()):
            mins, maxes = val
            # Data has been decimated.  Plot as a series of lines from min to
            # max.
            for i in range(len(mins)):
                starts = np.column_stack((idx, mins[i]))
                ends = np.column_stack((idx, maxes[i]))
                gc.line_set(starts, ends)
        else:
            # Data has not been decimated.  Plot as a standard connected line
            # plot.
            gc.lines(np.column_stack((idx, val)))

        gc.stroke_path()
        self._render_channel_numbers(gc)
        self._draw_default_axes(gc)
        gc.restore_state()

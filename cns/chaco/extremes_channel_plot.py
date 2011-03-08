import numpy as np
from channel_plot import ChannelPlot
from enthought.traits.api import List

def decimate_extremes(data, downsample):
    # Axis that we want to decimate across
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
    Often our neurophysiology data involves sampling at up to 200kHz.  If we
    are viewing a second's worth of data on screen using standard plotting
    functions, then this means we are computing the data to screen coordinate
    transform of 200,000 points every few milliseconds and then blitting this to
    screen.

    instead, each time a new call to render the plot on screen is made (e.g.
    there's new data, the screen is resized, or the data bounds change), the
    data is downsampled so there is only one vertical "line" per screen pixel.
    The line runs from the minimum to the maximum.  This is great for plotting
    neurophysiology data since you can see the noise floor and individual spikes
    will show up quite well.

    In cases where there are fewer data points than screen pixels, then the plot
    reverts to a standard "connected" XY plot.
    '''

    offset = 0.5e-3
    visible = List([1, 2, 3, 4, 5, 6])

    def _get_screen_points(self):
        if not self._screen_cache_valid:
            # Get the decimated data
            decimation_factor = self._decimation_factor()
            cached_data = self._cached_data[self.visible]
            values = decimate_extremes(cached_data, decimation_factor)

            if type(values) == type(()):
                channels, samples = values[0].shape
                offsets = self.offset*np.arange(channels)[:,np.newaxis]
                s_val_min = self.value_mapper.map_screen(values[0]+offsets) 
                s_val_max = self.value_mapper.map_screen(values[1]+offsets) 
                self._cached_screen_data = s_val_min, s_val_max
            else:
                channels, samples = values.shape
                offsets = self.offset*np.arange(channels)[:np.newaxis]
                s_val_pts = self.value_mapper.map_screen(values+offsets) 
                self._cached_screen_data = s_val_pts

            total_samples = self._cached_data.shape[-1]
            t = self.index_values[:total_samples:decimation_factor][:samples]
            t_screen = self.index_mapper.map_screen(t)
            self._cached_screen_index = t_screen
            self._screen_cache_valid = True

        return self._cached_screen_index, self._cached_screen_data

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
        self._draw_default_axes(gc)
        gc.restore_state()

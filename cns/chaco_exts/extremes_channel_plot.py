import numpy as np
from channel_plot import ChannelPlot
from enthought.traits.api import (List, Float, on_trait_change, Any, Property,
        cached_property)

import logging
log = logging.getLogger(__name__)

def decimate_simple(data, downsample):
    if data.shape[-1] == 0:
        return [], []

    # Determine the "fragment" size that we are unable to decimate.  A
    # downsampling factor of 5 means that we perform the operation in chunks of
    # 5 samples.  If we have only 13 samples of data, then we cannot decimate
    # the last 3 samples and will simply discard them. 
    last_dim = data.ndim
    offset = data.shape[-1] % downsample
    return data[..., ::downsample]

def decimate_extremes(data, downsample):
    # Axis that we want to decimate across
    if data.shape[-1] == 0:
        return [], []

    # Determine the "fragment" size that we are unable to decimate.  A
    # downsampling factor of 5 means that we perform the operation in chunks of
    # 5 samples.  If we have only 13 samples of data, then we cannot decimate
    # the last 3 samples and will simply discard them. 
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

#class ExtremesChannelPlot(ChannelPlot):
#    '''
#    Often our neurophysiology data involves sampling at up to 200kHz.  If we are
#    viewing a second's worth of data on screen using standard plotting
#    functions, then this means we are computing the data to screen coordinate
#    transform of 200,000 points every few milliseconds and then blitting this to
#    screen.
#
#    Instead, each time a new call to render the plot on screen is made (e.g.
#    there's new data, the screen is resized, or the data bounds change), the
#    data is downsampled so there is only one vertical "line" per screen pixel.
#    The line runs from the minimum to the maximum.  This is great for plotting
#    neurophysiology data since you can see the noise floor and individual spikes
#    will show up quite well.
#
#    In cases where there are fewer data points than screen pixels, then the plot
#    reverts to a standard "connected" XY plot.
#    '''
#
#    _cached_min     = Any(None)
#    _cached_max     = Any(None)
#
#    def _index_mapper_updated(self):
#        super(ExtremesChannelPlot, self)._index_mapper_updated()
#        # Compute number of decimated samples 
#        self._cached_min = None
#        self._cached_max = None
#
#    def _get_screen_points(self):
#        if not self._screen_cache_valid:
#            if self._cached_data.shape[-1] == 0:
#                self._cached_screen_data = []
#                self._cached_screen_index = []
#            else:
#                decimation_factor = self._decimation_factor()
#
#                # Don't recompute region of data that we've already done on a
#                # prior pass.  Prior computations are cached in _cached_min and
#                # _cached_max.  Determine what region of the data is new and
#                # append it.
#                if self._cached_min is not None:
#                    n_cached = self._cached_min.shape[-1]*decimation_factor
#                    to_decimate = self._cached_data[..., n_cached:]
#                    mins = decimate_simple(to_decimate, decimation_factor)
#                    maxes = mins.copy()
#                    self._cached_min = np.hstack((self._cached_min, mins))
#                    self._cached_max = np.hstack((self._cached_max, maxes))
#                else:
#                    mins, maxes = decimate_extremes(self._cached_data, decimation_factor)
#                    self._cached_min = mins
#                    self._cached_max = maxes
#
#                # Now, map them to the screen
#                samples = self._cached_min.shape[-1]
#                mins = self._cached_min
#                s_val_min = self.value_mapper.map_screen(mins)
#                maxes = self._cached_max
#                s_val_max = self.value_mapper.map_screen(maxes)
#                self._cached_screen_data = s_val_min, s_val_max
#
#                total_samples = self._cached_data.shape[-1]
#                t = self.index_values[:total_samples:decimation_factor][:samples]
#                t_screen = self.index_mapper.map_screen(t)
#                self._cached_screen_index = t_screen
#                self._screen_cache_valid = True
#
#        return self._cached_screen_index, self._cached_screen_data
#
#    def _render(self, gc, points):
#        idx, (mins, maxes) = points
#        if len(idx) == 0:
#            return
#
#        gc.save_state()
#        gc.clip_to_rect(self.x, self.y, self.width, self.height)
#        gc.set_stroke_color(self.line_color_)
#        gc.set_line_width(self.line_width) 
#
#        gc.begin_path()
#        for i in range(len(mins)):
#            starts = np.column_stack((idx, mins))
#            ends = np.column_stack((idx, maxes))
#            gc.line_set(starts, ends)
#
#        gc.stroke_path()
#        self._draw_default_axes(gc)
#        gc.restore_state()

class ExtremesChannelPlot(ChannelPlot):

    # Offset of all channels along the value axis
    channel_offset  = Float(0.25e-3)

    # Distance between each channel along the value axis
    channel_spacing = Float(0.5e-3)

    # Which channels are visible?
    channel_visible = List([])

    offsets = Property(depends_on='channel_spacing, channel_offset, channel_visible')
    text_screen_offsets = Property(depends_on='offsets')

    # Offset, spacing and visible only affect the screen points, so we only
    # invalidate the screen cache.  The data cache is fine.

    _cached_min     = Any
    _cached_max     = Any

    def _index_mapper_updated(self):
        super(ExtremesChannelPlot, self)._index_mapper_updated()
        self._cached_min = None
        self._cached_max = None

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

    def _get_screen_points(self):
        if not self._screen_cache_valid:
            if self._cached_data.shape[-1] == 0:
                self._cached_screen_data = [], []
                self._cached_screen_index = []
            else:
                if len(self.channel_visible) == 0:
                    self._cached_screen_data = [], []
                    self._cached_screen_index = []
                    self._screen_cache_valid = True
                    return self._cached_screen_index, self._cached_screen_data
                    
                decimation_factor = self._decimation_factor()

                if self._cached_min is not None:
                    n_cached = self._cached_min.shape[-1]*decimation_factor
                    to_decimate = self._cached_data[..., n_cached:]
                    mins, maxes = decimate_extremes(to_decimate, decimation_factor)
                    self._cached_min = np.hstack((self._cached_min, mins))
                    self._cached_max = np.hstack((self._cached_max, maxes))
                else:
                    mins, maxes = decimate_extremes(self._cached_data, decimation_factor)
                    self._cached_min = mins
                    self._cached_max = maxes

                # Now, map them to the screen
                channels, samples = self._cached_min.shape
                mins = self._cached_min[self.channel_visible] + self.offsets
                s_val_min = self.value_mapper.map_screen(mins)
                maxes = self._cached_max[self.channel_visible] + self.offsets
                s_val_max = self.value_mapper.map_screen(maxes)
                self._cached_screen_data = s_val_min, s_val_max

                total_samples = self._cached_data.shape[-1]
                t = self.index_values[:total_samples:decimation_factor][:samples]
                t_screen = self.index_mapper.map_screen(t)
                self._cached_screen_index = t_screen
                self._screen_cache_valid = True

        return self._cached_screen_index, self._cached_screen_data

    def _render(self, gc, points):
        idx, (mins, maxes) = points
        if len(idx) == 0:
            return

        gc.save_state()
        gc.clip_to_rect(self.x, self.y, self.width, self.height)
        gc.set_stroke_color(self.line_color_)
        gc.set_line_width(self.line_width) 

        gc.begin_path()
        for i in range(len(mins)):
            starts = np.column_stack((idx, mins[i]))
            ends = np.column_stack((idx, maxes[i]))
            gc.line_set(starts, ends)

        gc.stroke_path()
        self._draw_default_axes(gc)
        gc.restore_state()

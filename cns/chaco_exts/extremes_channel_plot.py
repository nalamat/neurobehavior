from __future__ import division

import numpy as np
from channel_plot import ChannelPlot
from enthought.traits.api import (List, Float, on_trait_change, Any, Property,
        cached_property, Enum, Int)
from enthought.enable.api import ColorTrait, black_color_trait
from enthought.traits.ui.api import View, Item
from itertools import cycle

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
    # If data is empty, return imediately
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

class ExtremesChannelPlot(ChannelPlot):

    # Offset of all channels along the value axis
    channel_offset  = Float(0.25e-3)

    # Distance between each channel along the value axis
    channel_spacing = Float(0.5e-3)

    # Which channels are visible?
    channel_visible = List([])

    offsets = Property(depends_on='channel_+, value_mapper.updated')
    screen_offsets = Property(depends_on='offsets')

    # Offset, spacing and visible only affect the screen points, so we only
    # invalidate the screen cache.  The data cache is fine.

    _cached_min     = Any
    _cached_max     = Any

    # At what point should we switch from generating a decimated plot to a
    # regular line plot?
    dec_threshold = Int(6)
    draw_mode = Property(depends_on='dec_threshold, dec_factor')

    #alternate_colors = Bool(False)
    #alternate_line_color = ColorTrait('darkblue')
    alternate_line_color = black_color_trait

    _line_color_iter = Property(depends_on='line_color, alternate_line_color')

    @cached_property
    def _get__line_color_iter(self):
        return cycle((self.line_color_, self.alternate_line_color_))

    def _dec_points_changed(self):
        # Flush the downsampled cache since it is no longer valid
        self._cached_min = None
        self._cached_max = None

    @cached_property
    def _get_draw_mode(self):
        return 'ptp' if self.dec_factor >= self.dec_threshold else 'normal'

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

    @cached_property
    def _get_screen_offsets(self):
        return self.value_mapper.map_screen(self.offsets)

    def _get_screen_points(self):
        print 'getting points', self._screen_cache_valid
        print 'cached data', self._cached_data.shape, self.channel_visible
        if not self._screen_cache_valid:
            if self._cached_data.shape[-1] == 0:
                self._cached_screen_data = [], []
                self._cached_screen_index = []
            elif len(self.channel_visible) == 0:
                self._cached_screen_data = [], []
                self._cached_screen_index = []
                self._screen_cache_valid = True
            else:
                if self.draw_mode == 'normal':
                    self._compute_screen_points_normal()
                else:
                    self._compute_screen_points_decimated()
        return self._cached_screen_index, self._cached_screen_data

    def _compute_screen_points_normal(self):
        print 'here'
        mapped = self._map_screen(self._cached_data)
        t = self.index_values[:mapped.shape[-1]]
        t_screen = self.index_mapper.map_screen(t)
        self._cached_screen_data = mapped 
        self._cached_screen_index = t_screen
        self._screen_cache_valid = True

    def _map_screen(self, data):
        spaced_data = data[self.channel_visible] + self.offsets
        return self.value_mapper.map_screen(spaced_data)

    def _compute_screen_points_decimated(self):
        # We cache our prior decimations 
        print 'getting', self._cached_data.shape
        if self._cached_min is not None:
            n_cached = self._cached_min.shape[-1]*self.dec_factor
            to_decimate = self._cached_data[..., n_cached:]
            mins, maxes = decimate_extremes(to_decimate, self.dec_factor)
            self._cached_min = np.hstack((self._cached_min, mins))
            self._cached_max = np.hstack((self._cached_max, maxes))
        else:
            ptp = decimate_extremes(self._cached_data, self.dec_factor)
            self._cached_min = ptp[0]
            self._cached_max = ptp[1]

        # Now, map them to the screen
        channels, samples = self._cached_min.shape
        s_val_min = self._map_screen(self._cached_min)
        s_val_max = self._map_screen(self._cached_max)
        self._cached_screen_data = s_val_min, s_val_max

        total_samples = self._cached_data.shape[-1]
        t = self.index_values[:total_samples:self.dec_factor][:samples]
        t_screen = self.index_mapper.map_screen(t)
        self._cached_screen_index = t_screen
        self._screen_cache_valid = True

    def _render(self, gc, points):
        if len(points[0]) == 0:
            return

        gc.save_state()
        gc.clip_to_rect(self.x, self.y, self.width, self.height)
        #gc.set_stroke_color(self.line_color_)
        gc.set_line_width(self.line_width) 

        gc.begin_path()
        if self.draw_mode == 'normal':
            idx, val = points
            for v, c in zip(val, self._line_color_iter):
                gc.set_stroke_color(c)
                gc.lines(np.c_[idx, v])
                gc.stroke_path()
        else:
            idx, (mins, maxes) = points
            for i, c in zip(range(len(mins)), self._line_color_iter):
                gc.set_stroke_color(c)
                starts = np.column_stack((idx, mins[i]))
                ends = np.column_stack((idx, maxes[i]))
                gc.line_set(starts, ends)
                gc.stroke_path()

        self._draw_default_axes(gc)
        gc.restore_state()

    traits_view = View(
            Item('dec_points', label='Samples per pixel'),
            Item('dec_threshold', label='Decimation threshold'),
            Item('draw_mode', style='readonly'),
            #Item('fill_color'),
            Item('line_color'),
            Item('line_width'),
            #Item('alternate_color'),
            Item('alternate_line_color'),

            )

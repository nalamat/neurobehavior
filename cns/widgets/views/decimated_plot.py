from __future__ import division
from cns.channel import Channel
from enthought.chaco.api import BaseXYPlot
from enthought.enable.api import black_color_trait, LineStyle
from enthought.traits.api import Float, Int, Instance, HasTraits, Trait, Bool, \
    Event, Str, Enum
from enthought.traits.ui.api import View
import numpy as np

def decimate(data, screen_width, downsampling_cutoff=4, mode='extremes'):
    data_width = len(data)
    downsample = np.floor((data_width/screen_width)/4.)
    if downsample > downsampling_cutoff:
        return globals()['decimate_'+mode](data, downsample)
    else:
        return data

def decimate_extremes(data, downsample):
    offset = len(data) % downsample
    # Force a copy to be made, which speeds up min()/max().  Apparently min/max
    # make a copy of a reshaped array before performing the operation, so we
    # force it now so the copy only occurs once.
    if data.ndim == 2:
        shape = (-1, downsample, data.shape[-1])
    else:
        # If channels attribute is not set, it's a single channel.
        shape = (-1, downsample)
    data = data[offset:].reshape(shape).copy()
    data_min = data.min(1)
    data_max = data.max(1)
    #return np.vstack[data_min, data_max], True
    #return np.column_stack((data_min, data_max)), True
    return data_min, data_max

def decimate_mean(data, downsample):
    offset = len(data) % downsample
    if data.ndim == 2:
        shape = (-1, downsample, data.shape[-1])
    else:
        # If channels attribute is not set, it's a single channel.
        shape = (-1, downsample)
    data = data[offset:].reshape(shape).copy()
    return data.mean(1)

class ChannelDataSource(HasTraits):
    # We could derive from the AbstractDataSource in enthought.chaco package;
    # however, I find that we don't really need a lot of the required methods
    # that it stubs out.
    
    channel = Instance(Channel)
    
    _data_cache_valid = Bool(False)
    _dec_cache_valid = Bool(False)
    downsampling_cutoff = Int(4)
    data_changed = Event
    decimate_mode = Str('extremes')
    reference = Enum('last_sample', 'trigger')
    
    def get_bounds(self):
        return self._data_cache_bounds
    
    def get_data(self, lb, ub, reference=None, channel=None):
        # Since the get_range operation is sometimes time-consuming depending on
        # the type of channel (e.g. a file-based channel can be very slow since
        # it hits the disk each time), we store the data in a cache.
        if not self._data_cache_valid or self._data_cache_pars != (lb,  ub, reference):
            if self.reference == 'last_sample':
                self._data_cache, lb, ub = self.channel.get_recent_range(lb, ub) 
            else:
                self._data_cache, lb, ub = self.channel.get_range(lb, ub, -1) 
            self._data_cache_bounds = lb, ub
            self._data_cache_valid = True
            self._data_cache_pars = (lb, ub, reference)
        if channel is not None:
            return self._data_cache[:,channel]
        else:
            return self._data_cache
        
    def get_decimated_data(self, lb, ub, reference, screen_width, channel=None):
        if not self._dec_cache_valid or \
                self._dec_cache_pars != (lb, ub, reference, screen_width):
            # TODO: I think we need to get the full set of data, decimate it,
            # and cache it.  If we're only plotting one channel, then we should
            # consider having a listener on this to turn off the inactive
            # channels so we don't waste time computing them.
            data = self.get_data(lb, ub, reference)
            self._dec_cache = decimate(data, screen_width,  self.downsampling_cutoff,
                                       self.decimate_mode)
            self._dec_cache_valid = True
            self._dec_cache_pars = (lb, ub, reference, screen_width)
                
        if channel is not None:
            if type(self._dec_cache) == type(()):
                result = self._dec_cache[0][:,channel], self._dec_cache[1][:,channel]
                return result
            else:
                return self._dec_cache[:, channel]
        else:
            return self._dec_cache
        
    def _data_changed(self):
        self._data_cache_valid = False
        self._dec_cache_valid = False
        self.data_changed = True
        
    def _channel_changed(self, old, new):
        if old is not None:
            old.on_trait_change(self._data_changed, "updated", remove=True)
        if new is not None:
            new.on_trait_change(self._data_changed, "updated", dispatch="new")
    
class TimeSeries(BaseXYPlot):
    '''
    Often our neurophysiology data involves sampling at up to 200kHz.  If we
    are viewing a second's worth of data on screen using standard plotting
    functions, then this means we are computing the data to screen coordinate
    transform of 200,000 points every few milliseconds and then blitting this to
    screen.

    This function speeds up plotting using two approaches.

    1.  Each time a new call to render the plot on screen is made (e.g. there's
    new data, the screen is resized, or the data bounds change), the data is
    downsampled so there is only one vertical "line" per screen pixel.  The line
    runs from the minimum to the maximum.  This is great for plotting
    neurophysiology data since you can see the noise floor and individual spikes
    will show up quite well.

    In cases where there are fewer data points than screen pixels, then the plot
    reverts to a standard "connected" XY plot.

    2.  TODO: is this true?  Have I implemented this???  Unless the user zooms
    or pans, the screen transforms for the X-axis (index) do not need to be
    re-computed.  
    '''
    
    color = black_color_trait
    line_width = Float(1.0)
    line_style = LineStyle
    reference = Enum('most_recent', 'trigger')

    traits_view = View("color@", "line_width")
    downsampling_cutoff = Int(4)
    
    channel = Instance(HasTraits)
    signal_trait = "updated"
    
    decimate_mode = Str('extremes')
    
    ch_index = Trait(None, Int, None)
    
    def get_screen_points(self):
        self._gather_points()
        return self._downsample()
    
    def _data_changed(self):
        self.invalidate_draw()
        self._cache_valid = False
        self._screen_cache_valid = False
        self.request_redraw()
    
    def _gather_points(self):
        if not self._cache_valid:
            range = self.index_mapper.range
            if self.reference == 'most_recent':
                values, t_lb, t_ub = self.channel.get_recent_range(range.low, range.high)
            else:
                values, t_lb, t_ub = self.channel.get_range(range.low, range.high, -1)
            if self.ch_index is None:
                self._cached_data = values
            else:
                self._cached_data = values[:,self.ch_index]
            self._cached_data_bounds = t_lb, t_ub
            self._cache_valid = True
            self._screen_cache_valid = False
            
    def _downsample(self):
        if not self._screen_cache_valid:
            val_pts = self._cached_data
            screen_min, screen_max = self.index_mapper.screen_bounds
            screen_width = screen_max-screen_min
            #decimate(val_pts, screen_width, self.downsampling_cutoff)
            values = decimate(val_pts, screen_width, self.downsampling_cutoff,
                              self.decimate_mode)
            if type(values) == type(()):
                n = len(values[0])
                s_val_min = self.value_mapper.map_screen(values[0]) 
                s_val_max = self.value_mapper.map_screen(values[1]) 
                self._cached_screen_data = s_val_min, s_val_max
            else:
                s_val_pts = self.value_mapper.map_screen(values) 
                self._cached_screen_data = s_val_pts
                n = len(values)
            
            t = np.linspace(*self._cached_data_bounds, num=n)
            t_screen = self.index_mapper.map_screen(t)
            self._cached_screen_index = t_screen
            self._screen_cache_valid = True
            
        return [self._cached_screen_index, self._cached_screen_data]
    
    def _render(self, gc, points):
        idx, val = points
        if len(idx) == 0:
            return

        gc.save_state()
        gc.set_antialias(True)
        gc.clip_to_rect(self.x, self.y, self.width, self.height)
        gc.set_stroke_color(self.color_)
        gc.set_line_width(self.line_width) 
        #gc.set_line_width(5) 
        gc.begin_path()

        #if len(val) == 2:
        if type(val) == type(()):
            starts = np.column_stack((idx, val[0]))
            ends = np.column_stack((idx, val[1]))
            gc.line_set(starts, ends)
        else:
            gc.lines(np.column_stack((idx, val)))

        gc.stroke_path()
        self._draw_default_axes(gc)
        gc.restore_state()
        
    def _channel_changed(self, old, new):
        if old is not None:
            old.on_trait_change(self._data_changed, self.signal_trait, remove=True)
        if new is not None:
            new.on_trait_change(self._data_changed, self.signal_trait, dispatch="new")

class TTLTimeSeries(TimeSeries):

    def _gather_points(self):
        if not self._cache_valid:
            range = self.index_mapper.range
            if self.reference == 'most_recent':
                values, t_lb, t_ub = self.channel.get_recent_range(range.low, range.high)
            else:
                values, t_lb, t_ub = self.channel.get_range(range.low, range.high, -1)
            #values = values.astype('f')
            #jnp.putmask(values, values==0, np.nan)
            #print values 

            if self.ch_index is None:
                self._cached_data = values
            else:
                self._cached_data = values[:,self.ch_index]
            self._cached_data_bounds = t_lb, t_ub
            self._cache_valid = True
            self._screen_cache_valid = False
            
class SharedTimeSeries(TimeSeries):

    channel = Instance(ChannelDataSource)
    signal_trait = "data_changed"
    channel_index = Trait(None, Int)
    
    def get_screen_points(self):
        if not self._screen_cache_valid:
            screen_min, screen_max = self.index_mapper.screen_bounds
            screen_width = screen_max-screen_min
            range = self.index_mapper.range
            values = self.channel.get_decimated_data(range.low, 
                                                     range.high, -1, 
                                                     screen_width, 
                                                     self.channel_index)
            if type(values) == type(()):
                s_min = self.value_mapper.map_screen(values[0]) 
                s_max = self.value_mapper.map_screen(values[1]) 
                self._screen_value_cache = s_min, s_max
                n = len(s_min)
            else:
                s = self.value_mapper.map_screen(values) 
                self._screen_value_cache = s
                n = len(s)
            t = np.linspace(*self.channel.get_bounds(), num=n)
            s_t = self.index_mapper.map_screen(t)
            self._screen_index_cache = s_t
            self._screen_cache_valid = True
            
        return [self._screen_index_cache, self._screen_value_cache]

import numpy as np

from .channel_plot import ChannelPlot
from enable.api import black_color_trait, LineStyle, MarkerTrait, ColorTrait
from traits.api import Instance, Float

class EpochRectPlot(ChannelPlot):
    '''
    Designed for efficiently handling time series data stored in a channel.
    Each time a Channel.updated event is fired, the new data is obtained and
    plotted.

    Example:
        value_range = DataRange1D(low_setting=0, high_setting=1)
        value_mapper = LinearMapper(range=value_range)
        plot = EpochRectPlot(source=self.data.poke_epoch,
            rect_color=(0,1,0,.5), rect_ypos=0.25, rect_height=0.5,
            index_mapper=index_mapper, value_mapper=value_mapper)
        container.add(plot)
    '''

    source = Instance('cns.channel.Epoch')
    rect_color  = black_color_trait
    rect_ypos   = Float(0.25)
    rect_height = Float(0.5)

    def _get_screen_points(self):
        if not self._screen_cache_valid:
            screen_index = self.index_mapper.map_screen(self._cached_data)
            screen_position = self.value_mapper.map_screen(self.rect_ypos)
            screen_value = np.ones(len(screen_index))*screen_position
            self._cached_screen_points = np.c_[screen_index, screen_value]
            self._screen_cache_valid = True
        return self._cached_screen_points

    def _render(self, gc, points):
        if len(points) == 0:
            return

        with gc:
            gc.clip_to_rect(self.x, self.y, self.width, self.height)

            gc.set_fill_color(self.rect_color_)
            gc.set_line_width(0)

            x = points[:,0]
            w = points[:,1]-x
            y = points[:,2]
            h = np.ones(len(x))*self.value_mapper.map_screen(self.rect_height)

            gc.begin_path()
            gc.rects(np.column_stack((x,y,w,h)))
            gc.draw_path()

            self._draw_default_axes(gc)

    def _data_added(self, timestamps):
        # Only fire an update if the changed data is within bounds
        if self.index_range.mask_data(np.array(timestamps)).any():
            self._invalidate_data()
            self.invalidate_draw()
            self.request_redraw()

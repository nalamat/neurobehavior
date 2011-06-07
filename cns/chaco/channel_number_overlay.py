from enthought.chaco.abstract_overlay import AbstractOverlay
from enthought.traits.api import Any, Property, cached_property
from enthought.enable.api import ColorTrait
from enthought.kiva import fonttools

class ChannelNumberOverlay(AbstractOverlay):

    plot = Any
    fill_color = ColorTrait('red')
    text_screen_offsets = Property(depends_on='plot.offsets')

    @cached_property
    def _get_text_screen_offsets(self):
        text_offsets = self.plot.offsets+self.plot.channel_spacing/3.0
        return self.plot.value_mapper.map_screen(text_offsets)

    def overlay(self, component, gc, view_bounds=None, mode="normal"):
        if len(self.plot.channel_visible) != 0:
            with gc:
                gc.set_font(fonttools.Font(size=24, weight=10))
                gc.clip_to_rect(component.x, component.y, component.width,
                        component.height)
                gc.set_fill_color(self.fill_color_)
                for o, n in zip(self.text_screen_offsets, self.plot.channel_visible):
                    gc.set_text_position(0, int(o))
                    gc.show_text(str(n+1))
from enthought.traits.api import Float
from enthought.enable.api import BaseTool
from enthought.chaco.tools.tool_history_mixin import ToolHistoryMixin

class ChannelRangeTool(BaseTool):

    index_factor = Float(1.5)

    def normal_mouse_enter(self, event):
        if self.component._window is not None:
            self.component._window._set_focus()

    def zoom_out_index(self, factor):
        self.component.index_mapper.range.span *= factor

    def zoom_in_index(self, factor):
        self.component.index_mapper.range.span /= factor

    def normal_left_down(self, event):
        self._start_data_x = self.component.index_mapper.map_data(event.x)
        self.event_state = "panning"
        event.window.set_pointer("hand")
        event.window.set_mouse_owner(self, event.net_transform())
        event.handled = True

    def panning_mouse_move(self, event):
        data_x = self.component.index_mapper.map_data(event.x)
        delta = data_x-self._start_data_x
        self.component.index_mapper.range.trig_delay += delta
        self._start_data_x = data_x

    def panning_left_up(self, event):
        self._end_pan(event)

    def panning_mouse_leave(self, event):
        self._end_pan(event)

    def _end_pan(self, event):
        self.event_state = 'normal'
        event.window.set_pointer("arrow")
        if event.window.mouse_owner == self:
            event.window.set_mouse_owner(None)
        event.handled = True

class MultiChannelRangeTool(ChannelRangeTool):

    value_span = Float(0.5e-3)
    value_factor = Float(1.1)

    def normal_mouse_wheel(self, event):
        if event.mouse_wheel != 0:
            if event.control_down:
                if event.mouse_wheel > 0:
                    factor = self.index_factor*event.mouse_wheel
                    self.zoom_in_index(factor)
                else:
                    factor = self.index_factor*abs(event.mouse_wheel)
                    self.zoom_out_index(factor)
            else:
                if event.mouse_wheel > 0:
                    factor = self.value_factor*event.mouse_wheel
                    self.zoom_in_value(factor)
                else:
                    factor = self.value_factor*abs(event.mouse_wheel)
                    self.zoom_out_value(factor)

    def zoom_in_value(self, factor):
        self.value_span *= factor
        self._update_value_range()

    def zoom_out_value(self, factor):
        self.value_span /= factor
        self._update_value_range()

    def _update_value_range(self):
        span = self.value_span
        visible = len(self.component.channel_visible)
        self.component.value_mapper.range.high_setting = visible*span
        self.component.value_mapper.range.low_setting = 0
        self.component.channel_offset = span/2.0
        self.component.channel_spacing = span

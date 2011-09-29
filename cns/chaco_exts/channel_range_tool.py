from enthought.traits.api import Float, Instance, on_trait_change
from enthought.enable.api import BaseTool, KeySpec
#from enthought.chaco.tools.tool_history_mixin import ToolHistoryMixin

class ChannelRangeTool(BaseTool):

    index_factor = Float(1.5)
    value_factor = Float(1.5)
    #reset_trig_delay_key = Instance(KeySpec, args=("0",))

    #def normal_key_pressed(self, event):
    #    if self.reset_trig_delay_key.match(event):
    #        self.component.index_mapper.range.trig_delay = 0

    def normal_mouse_enter(self, event):
        if self.component._window is not None:
            self.component._window._set_focus()

    def normal_mouse_wheel(self, event):
        if event.mouse_wheel != 0:
            if event.control_down:
                self.zoom_index(event)
            else:
                self.zoom_value(event)
            event.handled = True

    def normal_left_down(self, event):
        self._start_data_x = event.x
        self._start_delay = self.component.index_mapper.range.trig_delay
        self.event_state = "panning"
        event.window.set_pointer("hand")
        event.window.set_mouse_owner(self, event.net_transform())
        event.handled = True

    def panning_mouse_move(self, event):
        delta_screen = event.x-self._start_data_x
        data_0 = self.component.index_mapper.map_data(0)
        data_d = self.component.index_mapper.map_data(delta_screen)
        new_delay = self._start_delay+data_d-data_0
        self.component.index_mapper.range.trig_delay = new_delay

    def zoom_index(self, event):
        if event.mouse_wheel < 0:
            self.zoom_in_index(self.index_factor)
        else:
            self.zoom_out_index(self.index_factor)

    def zoom_out_index(self, factor):
        self.component.index_mapper.range.span *= factor

    def zoom_in_index(self, factor):
        self.component.index_mapper.range.span /= factor

    def zoom_value(self, event):
        if event.mouse_wheel < 0:
            self.zoom_in_value(self.value_factor)
        else:
            self.zoom_out_value(self.value_factor)

    def zoom_out_value(self, factor):
        self.component.value_mapper.range.low_setting *= factor
        self.component.value_mapper.range.high_setting *= factor

    def zoom_in_value(self, factor):
        self.component.value_mapper.range.low_setting /= factor
        self.component.value_mapper.range.high_setting /= factor

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

    def get_value_zoom_factor(self, event):
        return self.value_factor

    def normal_mouse_wheel(self, event):
        if event.mouse_wheel != 0:
            if event.control_down:
                if event.mouse_wheel < 0:
                    factor = self.get_value_zoom_factor(event)
                    self.zoom_in_index(factor)
                else:
                    factor = self.get_value_zoom_factor(event)
                    self.zoom_out_index(factor)
            else:
                if event.mouse_wheel < 0:
                    factor = self.get_value_zoom_factor(event)
                    self.zoom_in_value(factor)
                else:
                    factor = self.get_value_zoom_factor(event)
                    self.zoom_out_value(factor)

    def zoom_in_value(self, factor):
        self.value_span *= factor
        #self._update_value_range()

    def zoom_out_value(self, factor):
        self.value_span /= factor
        #self._update_value_range()

    @on_trait_change('value_span, component.channel_visible')
    def _update_span(self):
        span = self.value_span
        visible = len(self.component.channel_visible)
        self.component.value_mapper.range.high_setting = visible*span
        self.component.value_mapper.range.low_setting = 0
        self.component.channel_offset = span/2.0
        self.component.channel_spacing = span

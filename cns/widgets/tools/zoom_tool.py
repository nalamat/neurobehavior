from enthought.chaco.tools.simple_zoom import SimpleZoom
from enthought.traits.api import Enum, Instance, Property, Str
from enthought.enable.base_tool import KeySpec
from enthought.enable.events import KeyEvent

class RLZoomTool(SimpleZoom):
    
    enable_wheel        = True
    tool_mode           = 'range'
    
    def normal_right_down(self, event):
        if event.shift_down:
            self.axis = 'index'
            self._start_select(event)
            event.handled = True
            
    def normal_left_down(self, event):
        if event.shift_down:
            self.axis = 'value'
            self._start_select(event)
            event.handled = True
    
class ConstrainedZoomTool(SimpleZoom):

    enable_wheel        = False

    tool_mode           = 'box'
    index_constrain_key = Enum('shift', 'control', 'alt', None)
    value_constrain_key = Enum('control', 'shift', 'alt', None)

    enter_index_mode    = Instance(KeySpec, args=("i",))
    enter_value_mode    = Instance(KeySpec, args=("v",))
    enter_box_mode      = Instance(KeySpec, args=("b",))

    mode                = Property(Str)

    def _get_mode(self):
        return 'Index key = %s, value key = %s' % \
                (self.index_constrain_key, self.value_constrain_key)

    def _check_event(self, key, event):
        return key is not None and getattr(event, key+'_down')

    def _configure_constrain(self, event):
        # If index/value constrain keys are the same, then the tool mode will
        # default to box.
        constrain_index = self._check_event(self.index_constrain_key, event)
        constrain_value = self._check_event(self.value_constrain_key, event)

        if not constrain_index ^ constrain_value:
            self.tool_mode = 'box'
        else:
            self.tool_mode = 'range'
            self.axis = 'index' if constrain_index else 'value'

    def normal_mouse_wheel(self, event):
        self._configure_constrain(event)
        SimpleZoom.normal_mouse_wheel(self, event)

    def normal_key_pressed(self, event):
        self._configure_constrain(event)
        new_event = KeyEvent(
                character = event.character,
                alt_down = False,
                shift_down = False,
                control_down = False,
                handled = False,
                window = event.window)
        SimpleZoom.normal_key_pressed(self, new_event)

    def normal_left_down(self, event):
        self._configure_constrain(event)
        SimpleZoom.normal_left_down(self, event)

    def normal_right_down(self, event):
        self._configure_constrain(event)
        SimpleZoom.normal_right_down(self, event)

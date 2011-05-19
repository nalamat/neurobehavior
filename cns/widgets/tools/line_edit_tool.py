from enthought.enable.api import Component
from enthought.enable.base_tool import BaseTool
from enthought.traits.api import Bool, Enum, Tuple, Instance, Int, Float, List, Trait
from cns.util.math import ensure_monotonic
import numpy as np

class LineEditTool(BaseTool):
    """ Base class for tools that are activated by a drag operation.  
    
    This tool insulates the drag operation from double clicks and the like, and
    gracefully manages the transition into and out of drag mode.
    """
    component = Instance(Component)

    # The pixel distance from a point that the cursor is still considered
    # to be 'on' the point
    threshold = Int(25)

    # Cursor will snap to these points
    snap_x = Trait(None, Float)
    snap_y = Trait(None, Float)

    # The index of the point being dragged
    _drag_index = Int(-1)

    # The original dataspace values of the index and value datasources
    # corresponding to _drag_index
    _orig_value = Tuple

    # The mouse button used for this drag operation.
    drag_button = Enum("left", "right")

    # End the drag operation if the mouse leaves the associated component?
    end_drag_on_leave = Bool(True)
    
    # These keys, if pressed during drag, cause the drag operation to reset.
    cancel_keys = Tuple("Esc")
    
    mouse_down_position = Tuple(0.0, 0.0)

    # The modifier key that must be used to activate the tool.
    modifier_key = Enum("none", "shift", "alt", "control")

    # Whether or not to capture the mouse during the drag operation.  In
    # general this is a good idea.
    capture_mouse = Bool(True)

    # The possible states of this tool.
    _drag_state = Enum("nondrag", "dragging")
    
    # Records whether a mouse_down event has been received while in "nondrag"
    # state.  This is a safety check to prevent the tool from suddenly getting
    # mouse focus while the mouse button is down (either from window_enter or
    # programatically) and erroneously initiating a drag.
    _mouse_down_received = Bool(False)
    
    operations = List(Enum('add', 'delete'))
    drag_mode = Enum('XY', 'Y', 'X')
    monotonic = Bool(False)

    #------------------------------------------------------------------------
    # Interface for subclasses
    #------------------------------------------------------------------------
    def is_draggable(self, x, y):
        """ Returns whether the (x,y) position is in a region that is OK to 
        drag.  
        
        Used by the tool to determine when to start a drag.
        """
        return self.get_point(x, y) is not None

    def drag_start(self, event):
        """ Called when the drag operation starts.  
        
        The *event* parameter is the mouse event that established the drag 
        operation; its **x** and **y** attributes correspond to the current
        location of the mouse, and not to the position of the mouse when the 
        initial left_down or right_down event happened.
        """
        plot = self.component
        ndx = plot.map_index((event.x, event.y), self.threshold)
        if ndx is None:
            return
        self._drag_index = ndx
        self._orig_value = (plot.index.get_data()[ndx], plot.value.get_data()[ndx])

    def snap(self, x, y):
        if self.snap_x is not None:
            x = round(x/self.snap_x)*self.snap_x
        if self.snap_y is not None:
            y = round(y/self.snap_y)*self.snap_y
        return x, y
    
    def update_coordinates(self, x, y):
        if 'X' in self.drag_mode:
            self.component.index._data[self._drag_index] = x
        if 'Y' in self.drag_mode:
            self.component.value._data[self._drag_index] = y
            
        if self.monotonic:
            values = self.component.value._data
            values = ensure_monotonic(values, self._drag_index)
            self.component.value._data = values
        self.component.index.data_changed = True
        self.component.value.data_changed = True
        self.component.request_redraw()

    def dragging(self, event):
        """ This method is called for every mouse_move event that the tool 
        receives while the user is dragging the mouse.  
        
        It is recommended that subclasses do most of their work in this method.
        """
        plot = self.component
        data_x, data_y = self.snap(*plot.map_data((event.x, event.y)))

        if self._drag_index>0: 
            if plot.index._data[self._drag_index-1]>=data_x:
                #self._cancel_drag(event)
                return

        if self._drag_index+1<len(plot.index._data):
            if plot.index._data[self._drag_index+1]<=data_x:
                #self._cancel_drag(event)
                return
            
        self.update_coordinates(data_x, data_y)


    def drag_cancel(self, event):
        """ Called when the drag is canceled.
        
        A drag is usually canceled by receiving a mouse_leave event when 
        end_drag_on_leave is True, or by the user pressing any of the 
        **cancel_keys**.
        """
        self.update_coordinates(*self._orig_value)

    def drag_end(self, event):
        """ Called when a mouse event causes the drag operation to end.
        """
        plot = self.component
        if plot.index.metadata.has_key('selections'):
            del plot.index.metadata['selections']
        plot.invalidate_draw()
        plot.request_redraw()

    def get_point(self, x, y):
        return self.component.map_index((x, y), self.threshold)

    def normal_mouse_move(self, event):
        plot = self.component
        
        ndx = plot.map_index((event.x, event.y), self.threshold)
        if ndx is None:
            if plot.index.metadata.has_key('selections'):
                del plot.index.metadata['selections']
        else:
            plot.index.metadata['selections'] = [ndx]

        plot.invalidate_draw()
        plot.request_redraw()

    #------------------------------------------------------------------------
    # Private methods for handling drag
    #------------------------------------------------------------------------

    def _dispatch_stateful_event(self, event, suffix):
        # We intercept a lot of the basic events and re-map them if
        # necessary.  "consume" indicates whether or not we should pass
        # the event to the subclass's handlers.
        consume = False
        if suffix == self.drag_button + "_down":
            consume = self._drag_button_down(event)
        elif suffix == self.drag_button + "_up":
            consume = self._drag_button_up(event)
        elif suffix == "mouse_move":
            consume = self._drag_mouse_move(event)
        elif suffix == "mouse_leave":
            consume = self._drag_mouse_leave(event)
        elif suffix == "mouse_enter":
            consume = self._drag_mouse_enter(event)
        elif suffix == "key_pressed":
            consume = self._drag_cancel_keypressed(event)
        
        if not consume:
            BaseTool._dispatch_stateful_event(self, event, suffix)
        else:
            event.handled = True
        return

    def _cancel_drag(self, event):
        old_state = self._drag_state
        self._drag_state = "nondrag"
        if old_state == "dragging":
            self.drag_cancel(event)
        self._mouse_down_received = False
        if event.window.mouse_owner == self:
            event.window.set_mouse_owner(None)
        return

    def _drag_cancel_keypressed(self, event):
        if self._drag_state != "nondrag":
            self._cancel_drag(event)
            return True
        else:
            return False

    def _drag_mouse_move(self, event):
        state = self._drag_state
        button_down = getattr(event, self.drag_button + "_down")
        if state == "nondrag":
            if button_down and self._mouse_down_received and \
                   self.is_draggable(*self.mouse_down_position):
                self._drag_state = "dragging"
                if self.capture_mouse:
                    event.window.set_mouse_owner(self, transform=event.net_transform(),
                                                 history=event.dispatch_history)
                self.drag_start(event)
                return self._drag_mouse_move(event)
            return False
        elif state == "dragging":
            if button_down:
                return self.dragging(event)
            else:
                return self._drag_button_up(event)
        
        # If we don't invoke the subclass drag handler, then don't consume the event.
        return False

    def _drag_button_down(self, event):
        if self._drag_state == "nondrag":
            ndx = self.get_point(event.x, event.y)
            plot = self.component
            if ndx is not None and event.control_down:
                plot.index._data = np.delete(plot.index._data, ndx)
                plot.value._data = np.delete(plot.value._data, ndx)
                plot.index.data_changed = True
                plot.value.data_changed = True
                return False

            elif ndx is None and 'add' in self.operations:
                data_x, data_y = plot.map_data((event.x, event.y))
                index_data = np.r_[plot.index._data, data_x]
                value_data = np.r_[plot.value._data, data_y]
                i = np.argsort(index_data)
                plot.index._data = index_data[i]
                plot.value._data = value_data[i]
                plot.index.data_changed = True
                plot.value.data_changed = True

            self.mouse_down_position = (event.x, event.y)
            self._mouse_down_received = True

        return False

    def _drag_button_up(self, event):
        self._mouse_down_received = False
        state = self._drag_state
        if event.window.mouse_owner == self:
            event.window.set_mouse_owner(None)
        if state == "dragging":
            self._drag_state = "nondrag"
            return self.drag_end(event)
        
        # If we don't invoke the subclass drag handler, then don't consume the event.
        return False

    def _drag_mouse_leave(self, event):
        state = self._drag_state
        if self.end_drag_on_leave:
            self._mouse_down_received = False
            if state == "dragging":
                return self.drag_cancel(event)
            else:
                if event.window.mouse_owner == self:
                    event.window.set_mouse_owner(None)
        return False

    def _drag_mouse_enter(self, event):
        state = self._drag_state
        if state == "nondrag":
            pass
        elif state == "dragging":
            pass
        return False
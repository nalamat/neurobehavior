# Enthought library imports
from enthought.enable.api import cursor_style_trait, Line
from enthought.traits.api import Any, Bool, Enum, Instance, Int, List, Trait, \
        Tuple, HasTraits, Float, Property, Dict
from enthought.enable.component import Component

# Chaco imports
from enthought.chaco.api import AbstractOverlay

class SplineTool(AbstractOverlay):

    # The component that this tool overlays
    component = Instance(Component)
    
    # The current line segment being drawn.
    line = Instance(Line)

    event_state = Enum("normal", "selecting", "dragging")

    # The pixel distance from a vertex that is considered 'on' the vertex.
    proximity_distance = Int(8)

    # The data (index, value) position of the mouse cursor; this is used by various
    # draw() routines.
    mouse_position = Trait(None, None, Tuple)

    # The index of the vertex being dragged, if any.
    _dragged = Trait(None, None, Int)
    
    # Is the point being dragged is a newly placed point? This informs the
    # "dragging" state about what to do if the user presses Escape while
    # dragging.
    _drag_new_point = Bool(False)
    
    # The previous event state that the tool was in. This is used for states
    # that can be canceled (e.g., by pressing the Escape key), so that the
    # tool can revert to the correct state.
    _prev_event_state = Any

    # The cursor shapes to use for various modes
    
    # Cursor shape for non-tool use.
    original_cursor = cursor_style_trait("arrow")
    # Cursor shape for drawing.
    normal_cursor = cursor_style_trait("pencil")
    # Cursor shape for deleting points.
    delete_cursor = cursor_style_trait("bullseye")
    # Cursor shape for moving points.
    move_cursor = cursor_style_trait("sizing")

    # The tool is initially invisible, because there is nothing to draw.
    visible = Bool(False)

    def __init__(self, component=None, **kwtraits):
        if "component" in kwtraits:
            component = kwtraits["component"]
        super(SplineTool, self).__init__(**kwtraits)
        self.component = component
        self.reset()
    
    #------------------------------------------------------------------------
    # Drawing tool methods
    #------------------------------------------------------------------------
    def reset(self):
        """ Resets the tool, throwing away any points, and making the tool
        invisible.
        """
        self.line.points = []
        self.event_state = "normal"
        self.visible = False
        self.request_redraw()

    def _activate(self):
        """ Called by a PlotComponent when this becomes the active tool.
        """
        pass

    def _deactivate(self, component=None):
        """ Called by a PlotComponent when this is no longer the active tool.
        """
        self.reset()

    #------------------------------------------------------------------------
    # PointLine methods
    #------------------------------------------------------------------------
    def add_window(self, window):
        window.component = self.component
        self.windows.append(window)
        
    def set_window(self, index, window):
        """ Sets the data-space *index* for a screen-space *point*.
        """
        window.component = self.component
        self.windows[index] = window
    
    def remove_window(self, index):
        """ Removes the point for a given *index* from this tool's list of 
        points.
        """
        del self.windows[index]

    #------------------------------------------------------------------------
    # "normal" state
    #------------------------------------------------------------------------
    def normal_left_down(self, event):
        """ Handles the left mouse button being pressed while the tool is
        in the 'normal' state.
        
        For an existing point, if the user is pressing the Control key, the
        point is deleted. Otherwise, the user can drag the point.
        
        For a new point, the point is added, and the user can drag it.
        """
        # Determine if the user is dragging/deleting an existing point, or
        # creating a new one
        over = self._over_window(event, self.windows)
        if over is not None:
            if event.control_down:
                self.windows.pop(over[0]) # Delete the window
                self.request_redraw()
            else:
                self.event_state = "dragging"
                self._dragged = over
                self._drag_new_point = False
                self.dragging_mouse_move(event)
        elif len(self.windows) < self.max_windows:
            start_xy = event.x, event.y
            window = Window(screen_points=[start_xy, start_xy],
                            component=self.component)
            if event.shift_down:
                window.mode = 'EXCLUDE'
            self.windows.append(window)

            self._dragged = -1, 1 #e.g. last "window"
            self._drag_new_point = True
            self.visible = True
            self.event_state = "dragging"
            self.dragging_mouse_move(event)

    def normal_mouse_move(self, event):
        """ Handles the user moving the mouse in the 'normal' state.
        
        When the user moves the cursor over an existing point, if the Control 
        key is pressed, the cursor changes to the **delete_cursor**, indicating
        that the point can be deleted. Otherwise, the cursor changes to the
        **move_cursor**, indicating that the point can be moved.
        
        When the user moves the cursor over any other point, the cursor
        changes to (or stays) the **normal_cursor**.
        """
        # If the user moves over an existing point, change the cursor to be the
        # move_cursor; otherwise, set it to the normal cursor
        over = self._over_window(event, self.windows)
        if over is not None:
            if event.control_down:
                event.window.set_pointer(self.delete_cursor)
            else:
                event.window.set_pointer(self.move_cursor)
        else:
            event.handled = False
            if len(self.windows) < self.max_windows:
                event.window.set_pointer(self.normal_cursor)
            else:
                event.window.set_pointer(self.original_cursor)
        self.request_redraw()
    
    def normal_draw(self, gc):
        """ Draws the line.
        """
        for window in self.windows:
            window.line._draw(gc)
    
    def normal_key_pressed(self, event):
        """ Handles the user pressing a key in the 'normal' state.
        
        If the user presses the Enter key, the tool is reset.
        """
        if event.character == "Enter":
            self._finalize_selection()
            self.reset()

    def normal_mouse_leave(self, event):
        """ Handles the user moving the cursor away from the tool area.
        """
        event.window.set_pointer("arrow")
        
    #------------------------------------------------------------------------
    # "dragging" state
    #------------------------------------------------------------------------
    def dragging_mouse_move(self, event):
        """ Handles the user moving the mouse while in the 'dragging' state.
        
        The screen is updated to show the new mouse position as the end of the
        line segment being drawn.
        """
        window, point = self._dragged
        self.windows[window].update_screen_point(point, (event.x, event.y))
        self.request_redraw()

    def dragging_draw(self, gc):
        """ Draws the polygon in the 'dragging' state. 
        """
        for window in self.windows:
            window.line._draw(gc)

    def dragging_left_up(self, event):
        """ Handles the left mouse coming up in the 'dragging' state. 
        
        Switches to 'normal' state.
        """
        if self.windows[self._dragged[0]].distance < 4:
            self._cancel_drag()
        else:
            self.event_state = "normal"
            self._dragged = None
            self.updated = self
    
    def dragging_key_pressed(self, event):
        """ Handles a key being pressed in the 'dragging' state.
        
        If the key is "Esc", the drag operation is canceled.
        """
        if event.character == "Esc":
            self._cancel_drag()
    
    def dragging_mouse_leave(self, event):
        """ Handles the mouse leaving the tool area in the 'dragging' state.
        The drag is canceled and the cursor changes to an arrow.
        """
        self._cancel_drag()
        event.window.set_pointer("arrow")

    def _cancel_drag(self):
        """ Cancels a drag operation.
        """
        if self._dragged != None:
            if self._drag_new_point:
                # Only remove the point if it was a newly-placed point
                self.windows.pop(self._dragged[0])
            self._dragged = None
        self.mouse_position = None
        self.event_state = "normal"
        self.request_redraw()

    #------------------------------------------------------------------------
    # override AbstractOverlay methods
    #------------------------------------------------------------------------
    def overlay(self, component, gc, view_bounds, mode="normal"):
        """ Draws this component overlaid on another component.
        Implements AbstractOverlay.
        """
        draw_func = getattr(self, self.event_state + "_draw", None)
        if draw_func:
            gc.save_state()
            gc.clip_to_rect(component.x, component.y, component.width-1, component.height-1)
            draw_func(gc)
            gc.restore_state()
    
    def request_redraw(self):
        """ Requests that the component redraw itself. 
        Overrides Enable Component.
        """
        self.component.invalidate_draw()
        self.component.request_redraw()

    #------------------------------------------------------------------------
    # Private methods
    #------------------------------------------------------------------------
    def _over_window(self, event, windows):
        """ Return the index of a point in *points* that *event* is 'over'.
        Returns None if there is no such point.
        """
        for i, window in enumerate(windows):
            point = window._hittest(event)
            if point is not None:
                return i, point
        return None # If no _hittest passes

    def _finalize_selection(self):
        """Abstract method called to take action after the line selection is complete
        """
        pass
    
    #------------------------------------------------------------------------
    # Trait event handlers
    #------------------------------------------------------------------------
    def _component_changed(self, old, new):
        if new:
            self.container = new
        return

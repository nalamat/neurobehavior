from enthought.traits.api import Enum, Int, Instance, Dict, \
        on_trait_change, Property, Str
from enthought.traits.ui.api import Controller, Handler, HGroup, Item, \
        spring, View
from enthought.savage.traits.ui.svg_button import SVGButton
from enthought.etsconfig.api import ETSConfig
from enthought.pyface.api import error
from cns import equipment

from cns.widgets import icons
from cns.widgets.toolbar import ToolBar

def build_signal_cache(signal, *parameters):

    def generate_signal(template, parameter):
        signal = template.__class__()
        errors = signal.copy_traits(template)
        if errors:
            raise BaseException('Unable to copy traits to new signal')
        signal.set_variable(parameter)
        return signal

    cache = {}
    for par in parameters:
        cache[par] = generate_signal(signal, par)
    return cache

class ExperimentToolBar(ToolBar):

    size = 24, 24

    if ETSConfig.toolkit == 'qt4':
        kw = dict(height=size[0], width=size[1])
        apply = SVGButton('Apply', filename=icons.apply,
                          tooltip='Apply settings', **kw)
        revert = SVGButton('Revert', filename=icons.undo,
                          tooltip='Revert settings', **kw)
        start = SVGButton('Run', filename=icons.start,
                          tooltip='Begin experiment', **kw)
        pause = SVGButton('Pause', filename=icons.pause,
                          tooltip='Pause', **kw)
        resume = SVGButton('Resume', filename=icons.resume,
                          tooltip='Resume', **kw)
        stop = SVGButton('Stop', filename=icons.stop,
                          tooltip='stop', **kw)
        remind = SVGButton('Remind', filename=icons.warn,
                          tooltip='Remind', **kw)
        item_kw = dict(show_label=False)

    else:
        # The WX backend renderer for SVG buttons is ugly, so let's use text
        # buttons instead.  Eventually I'd like to unite these under ONE
        # backend.
        apply = Button('A')
        start = Button('>>')
        pause = Button('||')
        stop = Button('X')
        remind = Button('!')
        item_kw = dict(show_label=False, height=-size[0], width=-size[1])

    group = HGroup(Item('apply',
                        enabled_when="object.handler.pending_changes<>{}",
                        **item_kw),
                   Item('revert',
                        enabled_when="object.handler.pending_changes<>{}",
                        **item_kw),
                   Item('start',
                        enabled_when="object.handler.state=='halted'",
                        **item_kw),
                   '_',
                   Item('remind',
                        enabled_when="object.handler.state=='paused'",
                        **item_kw),
                   Item('pause',
                        enabled_when="object.handler.state=='running'",
                        **item_kw),
                   Item('resume',
                        enabled_when="object.handler.state=='paused'",
                        **item_kw),
                   Item('stop',
                        enabled_when="object.handler.state in " +\
                                     "['running', 'paused', 'manual']",
                        **item_kw),
                   spring,
                   springy=True,
                   )

    trait_view = View(group, kind='subpanel')

class ExperimentController(Controller):

    toolbar = Instance(ExperimentToolBar, ())
    #time_elapsed = Property(Str, depends_on='slow_tick', label='Time')
    
    # SYSTEM STATE
    # - Halted: The system is waiting for the user to configure parameters.  No
    #   data acquisition is in progress nor is a signal being played.  
    # - Paused: The system is configured, spout contact is being monitored, and
    #   the intertrial signal is being played. 
    # - Running: The system is playing the sequence of safe and warn signals. 
    # - Disconnected: Could not connect to the equipment.
    state = Enum('halted', 'paused', 'running', 'manual',  'disconnected')
    runs = Int(0)

    def init(self, info):
        self.model = info.object
        self.toolbar.install(self, info)
        try:
            self.init_equipment(info)
        except equipment.EquipmentError, e:
            self.state = 'disconnected'
            error(info.ui.control, str(e))
    
    def tick(self, speed):
        setattr(self, speed + '_tick', True)

    def _get_time_elapsed(self):
        if self.state is 'halted':
            return '%s' % timedelta()
        else:
            return '%s' % self.model.data.duration

    def close(self, info, is_ok):
        '''Prevent user from closing window while an experiment is running since
        data is not saved to file until the stop button is pressed.
        '''
        if self.state != 'halted':
            mesg = 'Please halt experiment before attempting to close window.'
            error(info.ui.control, mesg)
            return False
        else:
            return True    

    ############################################################################
    # Stubs to implement
    ############################################################################
    def start(self, info=None):
        error(info.ui.control, 'This action has not been implemented yet')
        raise NotImplementedError

    def resume(self, info=None):
        error(info.ui.control, 'This action has not been implemented yet')
        raise NotImplementedError

    def pause(self, info=None):
        error(info.ui.control, 'This action has not been implemented yet')
        raise NotImplementedError

    def remind(self, info=None):
        error(info.ui.control, 'This action has not been implemented yet')
        raise NotImplementedError

    def stop(self, info=None):
        error(info.ui.control, 'This action has not been implemented yet')
        raise NotImplementedError

    ############################################################################
    # Apply/Revert code
    ############################################################################
    # This code listens for any potential changes to the parameters listed under
    # paradigm.  All requested changes are captured and stored in a dictionary.
    # If a parameter is changed several times (before applying or reverting),
    # the dictionary is updated with the latest value.  To make a parameter
    # modifiable, an _apply_<parameter name> method must be available that
    # accepts the new value of the parameter and performs whatever work must be
    # done to apply this change.  If this method is not allowed, a warning will
    # be generated.

    pending_changes = Dict({})
    old_values = Dict({})

    @on_trait_change('object.model.paradigm.+')
    def queue_change(self, object, name, old, new):
        if self.state <> 'halted' and hasattr(self, '_apply_'+name):
            key = object, name
            if key not in self.old_values:
                self.old_values[key] = old
                self.pending_changes[key] = new
            elif new == self.old_values[key]:
                del self.pending_changes[key]
                del self.old_values[key]
            else:
                self.pending_changes[key] = new
        else:
            raise SystemError, 'cannot change parameter'

    def apply(self, info=None):
        ts = self.circuit.ts_n.value
        for key, value in self.pending_changes.items():
            object, name = key
            getattr(self, '_apply_'+name)(value)
            self.log_event(ts, name, value)
            del self.pending_changes[(object, name)]
            del self.old_values[(object, name)]

    def log_event(ts, name, value):
        log.debug('%d\tValue changed during experiment: %s = %r', ts, name,
                  value)
        
    def revert(self, info=None):
        '''Revert changes requested while experiment is running.'''
        for (object, name), value in self.old_values.items():
            log.debug('reverting changes for %s', name)
            setattr(object, name, value)
        self.old_values = {}
        self.pending_changes = {}

    def _apply_circuit_change(self, name, value, circuit=None):
        setattr(self.circuit, name, value)

if __name__ == '__main__':
    ExperimentToolBar().configure_traits()

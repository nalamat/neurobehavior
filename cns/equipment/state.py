from enthought.traits.api import HasTraits, Enum

class State(HasTraits):

    state = Enum('disconnected',
                 'idle',
                 'paused',
                 'running', 
                 'error',
                 'connected',
                 )

status = State()

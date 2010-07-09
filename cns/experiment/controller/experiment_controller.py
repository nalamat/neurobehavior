from enthought.traits.api import Enum
from enthought.traits.ui.api import Controller

class ExperimentController(Controller):
    
    # State of the system.  
    # Halted: The system is waiting for the user to configure parameters.  No
    # data acquisition is in progress nor is a signal being played.
    # Paused: The system is configured, spout contact is being monitored, and
    # the intertrial signal is being played.
    # Running: The system is playing the sequence of safe and warn signals.
    # Disconnected: Could not connect to the equipment.
    state = Enum('halted', 'paused', 'running', 'manual',  'disconnected')
    
    def tick(self, speed):
        setattr(self, speed + '_tick', True)
""" The Lorenz example application. """


# Standard library imports.
from logging import DEBUG

# Enthought library imports.
from enthought.envisage.ui.workbench.api import WorkbenchApplication
from enthought.envisage.ui.workbench.api import WorkbenchActionSet
from enthought.pyface.api import AboutDialog, ImageResource, SplashScreen

#class ActionSet(WorkbenchActionSet):
#    actions = [Action(path="MenuBar/File")]
#    #menus = [Menu(name='&Open', path='MenuBar')]

class LorenzApplication(WorkbenchApplication):
    """ The Lorenz example application. """

    # Globally unique ID
    id = 'cns.analysis'
    icon = ImageResource('lorenz.ico')
    
    # The name of the application (also used on window title bars etc).
    name = 'Behavior Analysis'

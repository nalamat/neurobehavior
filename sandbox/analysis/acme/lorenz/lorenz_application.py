from enthought.envisage.ui.workbench.api import WorkbenchApplication
from enthought.envisage.ui.workbench.api import WorkbenchActionSet
from enthought.pyface.api import AboutDialog, ImageResource, SplashScreen

#class ActionSet(WorkbenchActionSet):
#    actions = [Action(path="MenuBar/File")]
#    #menus = [Menu(name='&Open', path='MenuBar')]

class LorenzApplication(WorkbenchApplication):

    id = 'cns.analysis'
    icon = ImageResource('lorenz.ico')
    name = 'Behavior Analysis'

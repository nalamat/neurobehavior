'''
Created on Apr 20, 2010

@author: Brad
'''
from enthought.traits.api import *
from enthought.traits.ui.api import *
from enthought.traits.ui.menu import Action, Menu, MenuBar

class MainHandler(Handler):
    
    def init(self, info):
        actions = [Action(name='Load file', action='load_file'),
                   Action(name='Save file', action='save_file'),
                   Action(name='Save as file', action='saveas_file'), ]
        info.ui.view.menubar = MenuBar(Menu(*actions, name='File'))
        info.ui.updated = True
        
class MainWindow(HasTraits):
    
    a = Float
    b = Float
    
    view = View('a', 'b')
    
if __name__ == '__main__':
    
    MainWindow().configure_traits(handler=MainHandler)
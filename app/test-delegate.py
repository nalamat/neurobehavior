'''
Created on Jun 4, 2010

@author: admin_behavior
'''

from enthought.traits.api import *
from enthought.traits.ui.api import *

class Delegate(HasTraits):
    
    x = Int(1)

class TestDelegate(HasTraits):
    
    x = DelegatesTo('delegate')
    delegate = Instance(Delegate)
    
    def _delegate_default(self):
        return Delegate()

if __name__ == '__main__':
    TestDelegate().configure_traits()
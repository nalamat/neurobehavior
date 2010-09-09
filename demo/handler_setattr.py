'''
Created on May 11, 2010

@author: admin_behavior
'''

from enthought.traits.api import *
from enthought.traits.ui.api import *

class SubTestData(HasTraits):
    x = Int
    y = Float
    
class TestData(HasTraits):
    x = Int
    y = Float
    sub = Instance(SubTestData, ())
    
class TestHandler(Handler):
    def setattr(self, info, object, name, value):
        print 'setattr'
        
if __name__ == '__main__':
    TestData().configure_traits(handler=TestHandler())
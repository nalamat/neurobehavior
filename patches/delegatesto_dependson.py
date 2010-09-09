'''
Created on Jun 22, 2010

@author: admin_behavior
'''
from enthought.traits.api import *

class Test(HasTraits):
    
    a = Int(1)
    b = Int(2)
    x = Int(5)
    y = Int(4)
    z = Property(depends_on='x, y')
    
class TestChild(HasTraits):
    
    parent = Instance(Test)
    _ = DelegatesTo('parent')

if __name__ == '__main__':
    parent = Test()
    child = TestChild(parent=parent)
    
    print 'child.a=%d\tchild.x=%d' % (child.a, child.x)
    print 'parent.a=%d\tparent.x=%d' % (parent.a, parent.x)
    
    child.a = 11
    child.x = 55
    
    print 'child.a=%d\tchild.x=%d' % (child.a, child.x)
    print 'parent.a=%d\tparent.x=%d' % (parent.a, parent.x)
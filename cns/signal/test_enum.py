from enthought.traits.api import *
from enthought.traits.ui.api import *

class Foo(HasTraits):

    x = Enum('a', 'b', 'c', 'd')

    def x_changed(self, new):
        print 'x changed'

    @on_trait_change('x')
    def bar(self, new):
        print 'on trait change'

    view = View(Item('x', editor=EnumEditor(values=dict(a=1, b=2, c=3, d=4))))

Foo().configure_traits()

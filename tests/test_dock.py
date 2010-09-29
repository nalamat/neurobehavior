from enthought.traits.ui.api import *
from enthought.traits.api import *

class Foo(HasTraits):

    x = Int
    y = Int

    a = Int
    b = Int

    traits_view = View(Tabbed(VGroup('x', 'y', id='foo.x'),
                              VGroup('a', 'b', id='foo.y'),
                              id='foo.tabs'),
                       id='foo.main', 
		       dock='horizontal',
		       resizable=True)

Foo().configure_traits()

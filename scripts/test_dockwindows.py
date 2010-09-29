from enthought.etsconfig.api import ETSConfig
ETSConfig.toolkit = 'wx'
from enthought.traits.ui.api import *
from enthought.traits.api import *


class Foo(HasTraits):

    x = Float
    y = Str
    z = Int
    a = Range(0, 1)

    #traits_view = View(Tabbed(HSplit('x', 'y'), HSplit('z', 'a')),
    #                   id='cns.test')
    traits_view = View(Tabbed('x', 'y'), id='foo')

Foo().configure_traits()

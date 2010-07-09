from enthought.traits.api import *
from enthought.traits.ui.api import *

class MyData(HasTraits):

    infused = Float(10)

class MyController(Controller):

    data = Instance(MyData, ())
    infused = DelegatesTo('data')

class MySettings(HasTraits):

    traits_view = View(Item('^handler.infused', style='readonly'),
                       Item('^handler.data.infused', style='readonly'))

MySettings().configure_traits(handler=MyController())

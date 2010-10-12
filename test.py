from enthought.traits.api import *

class Test(HasTraits):

    x = Int

Test().configure_traits()

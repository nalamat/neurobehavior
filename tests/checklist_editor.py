from enthought.traits.api import *
from enthought.traits.ui.api import *

class Foo(HasTraits):

    ed = CheckListEditor(values=['1', '2', '3', '4'], cols=1)
    x = List(editor=ed)

    y = Button('Update list')

    def _y_fired(self):
        print self.ed.values
        self.ed.values.append('5')

    view = View(
            Item('x', style='custom'),
            Item('y'),
            resizable=True
            )

Foo().configure_traits()

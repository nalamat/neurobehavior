from enthought.traits.api import * 
from enthought.traits.ui.api import *
from enthought.traits.ui.table_column import ObjectColumn

from enthought.traits.ui.extras.checkbox_column import CheckboxColumn

class NiceColumn(ObjectColumn):
    width = 0.08
    horizontal_alignment = 'center'
    def get_text_color(self, object):
        return ['light grey', 'black'][object.visible]

ed = TableEditor(
        sortable=False,
        configurable=False,
        columns = [CheckboxColumn(name='visible', label='', width=0.12),
                   NiceColumn(name='num', editable=False),
                   NiceColumn(name='fs', editable=False),
                   ]
        )

class Channel(HasTraits):

    visible = Bool(True)
    num     = Int
    fs      = Float(1)

class Foo(HasTraits):

    ch = List(Channel)
    x = Button

    def _ch_default(self):
        return [Channel(num=1), Channel(num=2), Channel(num=3)]

    def _x_fired(self):
        self.ch.append(Channel(num=4))

    traits_view = View(
        Item('ch', editor=ed),
        Item('x'))

Foo().configure_traits()

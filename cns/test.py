from enthought.etsconfig.api import ETSConfig
ETSConfig.toolkit = 'qt4'
from enthought.traits.api import *
from enthought.traits.ui.api import *

class ParSetting(HasTraits):

    parameter = Float
    duration = Float
    rate = Float

table_editor = TableEditor(
        editable=True,
        deletable=True,
        edit_on_first_click=True,
        show_toolbar=True,
        row_factory=ParSetting,
        columns=[
            ObjectColumn(name='parameter'),
            ObjectColumn(name='duration'),
            ObjectColumn(name='rate'),
            ]
        )

class TestPar(HasTraits):

    pars = List(ParSetting, [ParSetting(parameter=0, duration=1, rate=2)])
    traits_view = View(Item('pars', editor=table_editor), resizable=True,
            height=400)

TestPar().configure_traits()

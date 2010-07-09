from enthought.chaco.api import *
from enthought.traits.api import *
from enthought.traits.ui.api import *
from enthought.enable.component_editor import ComponentEditor

import numpy as np

x = ArrayDataSource(data=np.arange(100))
y = ArrayDataSource(data=np.arange(100))

plot = FilledLinePlot(index=x, value=y,
                   index_mapper=LinearMapper(range=DataRange1D(low_setting=0,
                       high_setting=100)),
                   value_mapper=LinearMapper(range=DataRange1D(low_setting=0,
                       high_setting=100)),
                   face_color='black',
                   )
add_default_axes(plot)
container = OverlayPlotContainer(plot, resizable='hv', bgcolor='lightgray',
        fill_padding=True, padding=10, spacing=10)

class Test(HasTraits):

    plot = container
    view = View(Item('plot', editor=ComponentEditor()))

Test().configure_traits()

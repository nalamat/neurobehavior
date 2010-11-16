from enthought.traits.api import HasTraits, Instance, Str, Array, \
        CFloat, Property, cached_property, DelegatesTo,  \
        on_trait_change, Any, Trait, Enum
import numpy as np

from enthought.traits.ui.api import View, Item, VGroup, \
        Label, HGroup, InstanceEditor

from enthought.traits.ui.instance_choice import InstanceChoice

from enthought.enable.component_editor import ComponentEditor
from enthought.enable.component import Component
from enthought.enable.base_tool import KeySpec

from enthought.chaco.api import ArrayDataSource, BarPlot, create_bar_plot, \
        DataRange1D, LinearMapper, Plot, ArrayPlotData, LabelAxis, PlotAxis, \
        ScatterInspectorOverlay, LinePlot, create_line_plot, \
        OverlayPlotContainer, PlotLabel, BasePlotContainer, VPlotContainer

from enthought.chaco.tools.api import ScatterInspector, PanTool, \
        LassoSelection, RangeSelection, RangeSelectionOverlay, LineInspector, \
        ZoomTool

#####################################################################
# Experimental
#####################################################################
class Spacing(HasTraits):
    pass

class ManualSpacing(Spacing):

    values = Str('1 2 3 4 5')
    data = Property(Array(CFloat), depends_on='values')

    @cached_property
    def _get_data(self):
        return [float(v) for v in self.values.strip().split()]

    traits_view = View('values')

class SequenceSpacing(Spacing):

    start = CFloat(0)
    num_points = CFloat(10)
    step = CFloat(5)
    mode = Enum('linear', 'log')

    data = Property(Array, depends_on='start, num_points, step')

    @cached_property
    def _get_data(self):
        if self.mode == 'linear':
            lower = self.start
            upper = self.start + self.step * self.num_points
            return np.arange(lower, upper, self.step)
        elif self.mode == 'log':
            raise NotImplementedError

    traits_view = View('start{Start}',
                       'num_points{Number of points}',
                       'step{Step size}',
                       'mode{Step mode}')


spacing_selectors = {
        'manual':   ManualSpacing,
        'sequence': SequenceSpacing,
        }

class AxisSelector(HasTraits):

    selector = Instance(Spacing)
    data = DelegatesTo('selector')

    def _selector_default(self):
        return SequenceSpacing()

    def traits_view(self, parent=None):
        choices = [InstanceChoice(object=ManualSpacing()),
                   InstanceChoice(object=SequenceSpacing())]
        return View(Item('selector@', editor=InstanceEditor(values=choices)),
                    resizable=True)

class ScatterSelector(HasTraits):

    x = Instance(AxisSelector, ())
    y = Instance(AxisSelector, ())

    x_data = DelegatesTo('x', 'data')
    y_data = DelegatesTo('y', 'data')

    points = Property(Array, depends_on=['x_data', 'y_data'])

    container = Instance(Plot)
    data = Instance(ArrayPlotData)
    plot = Any

    def _data_default(self):
        data = ArrayPlotData()
        x, y = np.meshgrid(self.x_data, self.y_data)
        data.set_data('index', x.ravel())
        data.set_data('value', y.ravel())
        return data

    @on_trait_change('x_data, y_data')
    def set_data(self):
        x, y = np.meshgrid(self.x_data, self.y_data)
        self.data.set_data('index', x.ravel())
        self.data.set_data('value', y.ravel())

    def __init__(self, *args, **kw):
        HasTraits.__init__(self, *args, **kw)

        self.container = Plot(
            data=self.data,
            padding=50,
            fill_padding=True,
            bgcolor='white',
            border_visible=True,
            use_backbuffer=True,
            )

        #self.container.overlays.append(
        #        ConstrainedZoomTool(
        #            self.container,
        #            wheel_zoom_step=0.25,
        #            enter_zoom_key=KeySpec('z'),
        #            ),
        #        )
        self.container.tools.append(PanTool(self.container))

        self.plot = self.container.plot(('index', 'value'),
                'scatter',
                color='gray',
                line_width=0,
                marker='circle',
                marker_size=4,
                )[0]

        self.plot.tools.append(
                ScatterInspector(
                    self.plot,
                    selection_mode='single',
                    persistent_hover=False,
                    )
                )

        self.plot.overlays.append(
                ScatterInspectorOverlay(
                    self.plot,
                    hover_color='transparent',
                    hover_line_width=2,
                    hover_marker_size=6,
                    hover_outline_color='red',
                    selection_marker_size=6,
                    selection_marker='circle',
                    selection_color='black',
                    selection_line_width=0,
                    )
                )

        '''
        lasso_selection = LassoSelection(
                component=self.plot,
                selection_datasource=self.plot.index,
                )

        range_selection = RangeSelection(
                self.plot,
                #left_button_selects=True,
                )

        self.plot.overlays.append(
                LassoOverlay(
                    lasso_selection=lasso_selection,
                    component=self.plot,
                    )
                )

        self.plot.overlays.append(
                RangeSelectionOverlay(
                    component=self.plot,
                    )
                )

        #self.plot.active_tool = lasso_selection
        #self.plot.active_tool = range_selection
        '''

    view = View(
        HGroup(['x{}', 'y{}'],
            VGroup(
                Item('container',
                    editor=ComponentEditor(size=(400, 400)),
                    show_label=False
                    ),
                ),
            ),
        resizable=True,
        width=600,
        height=400,
        )

def test_selector():
    ScatterSelector().configure_traits()


if __name__ == '__main__':
    test_selector()

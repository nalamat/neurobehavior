from enthought.traits.api import *
from enthought.traits.ui.api import *
from enthought.traits.ui.menu import *
from enthought.pyface.timer.api import Timer
from enthought.enable.component_editor import ComponentEditor
from enthought.traits.ui.tabular_adapter import TabularAdapter

push_exception_handler(reraise_exceptions=True)

from enthought.chaco.api import *

import equipment
from cns.widgets.views.channel_view import AveragedChannelView
from cns.widgets.tools.api import WindowTool

from cns.channel import RepeatChannel

class Properties(HasTraits):

    pass

class MedusaController(Controller):

    props       = Instance(Properties)
    
    sig         = Instance(RepeatChannel, args=dict(samples=32, history=10))
    sig_buffer  = Any

    RX6         = Any
    RZ5         = Any

    sig_view    = Instance(AveragedChannelView)
    timer       = Instance(Timer)
    window_tool = Any
    
    update      = Button('update')      

    def _sig_view_default(self):
        self.sig.fs = self.RZ5.fs
        view = AveragedChannelView(
                value_min=-2e-4,
                value_max=2e-4,
                interactive=False,
                window=0.003,
                channel=self.sig,
                visual_aids=False,
                )
        self.window_tool = WindowTool(component=view.average_plot)
        view.average_plot.overlays.append(self.window_tool)
        return view

    def __init__(self, *args, **kwargs):
        Controller.__init__(self, *args, **kwargs)

        self.RX6 = equipment.backend.init_device('RepeatPlayRecord', 'RX6')
        self.RZ5 = equipment.backend.init_device('MedusaRecord_v4', 'RZ5')

        self.sig_buffer = self.RZ5.open('sp', 'r', multiple=32)
        self.RX6.trigger(1)
        self.timer = Timer(10, self.tick)

    def tick(self):
        self.sig.send(self.sig_buffer.next())
        
    def _update_fired(self):
        print self.window_tool.coordinates

plot_size = (400, 400)
view = View(
        VGroup(
            Item('handler.sig_view.container',
                editor=ComponentEditor(size=plot_size), 
                show_label=False,
                ),
            Item('handler.update'),
            ),
        height=400,
        width=400,
        resizable=True,
        )

def test_medusa():
    properties = Properties()
    handler = MedusaController(props=properties)
    properties.configure_traits(handler=handler, view=view)

if __name__ == '__main__':
    test_medusa()

from cns.widgets.toolbar import ToolBar
from enthought.etsconfig.api import ETSConfig
from enthought.traits.ui.api import View, HGroup, Item, Controller, VGroup
from enthought.traits.api import Instance, Bool, HasTraits, Button, Tuple, Float
from enthought.savage.traits.ui.svg_button import SVGButton
from cns.widgets import icons

from new_era import PumpInterface

class PumpToolBar(ToolBar):
    '''
    Toolbar containing command buttons that allow us to control the pump via a
    GUI.  Three basic commands are provided: increase rate, decrease rate, and
    override the TTL input (so pump continuously infuses). 
    '''

    kw               = dict(height=20, width=20, action=True)
    pump_override    = SVGButton('Run', filename=icons.right2, 
                                 tooltip='Override', toggle=True, **kw)
    pump_trigger     = SVGButton('Trigger', filename=icons.start,
                                 tooltip='Trigger', **kw)
    item_kw          = dict()

    traits_view = View(
            HGroup(Item('pump_override', **item_kw),
                   Item('pump_trigger', **item_kw),
                   enabled_when="object.handler.state<>'halted'",
                   show_labels=False,
                   ),
            )

class PumpControllerMixin(HasTraits):

    pump_toolbar        = Instance(PumpToolBar, (), toolbar=True)
    iface_pump          = Instance(PumpInterface, ())
    pump_toggle         = Bool(False)
    pump_trigger_cache  = Tuple
    pump_volume_cache   = Float

    def monitor_pump(self):
        infused = self.iface_pump.get_infused(unit='ml')
        ts = self.get_ts()
        self.model.data.log_water(ts, infused)

    def pump_trigger(self, info):
        self.iface_pump.run()

    def pump_override(self, info):
        if not self.pump_toggle:
            self.pump_trigger_cache = self.iface_pump.get_trigger()
            self.pump_volume_cache = self.iface_pump.get_volume()
            self.iface_pump.set_volume(0)
            self.iface_pump.set_trigger('rising', None)
            self.iface_pump.run()
            self.pump_toggle = True
        else:
            self.iface_pump.stop()
            self.iface_pump.set_trigger(*self.pump_trigger_cache)
            self.iface_pump.set_volume(self.pump_volume_cache)
            self.pump_toggle = False

    def set_pump_volume(self, value):
        self.iface_pump.pause()
        self.iface_pump.set_volume(value, unit='ul')
        self.iface_pump.resume()

    def set_pump_rate(self, value):
        self.iface_pump.pause()
        self.iface_pump.set_rate(value, unit='ml/min')
        self.iface_pump.resume()

    def set_pump_syringe_diameter(self, value):
        self.iface_pump.pause()
        self.iface_pump.set_diameter(value, unit='mm')
        self.iface_pump.resume()

    def set_pump_rate_delta(self, value):
        self.iface_pump.pause()
        self.current_pump_rate_delta = value
        self.iface_pump.resume()

if __name__ == '__main__':
    PumpToolBar().configure_traits()

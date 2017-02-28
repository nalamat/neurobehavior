from cns.widgets.toolbar import ToolBar
from traitsui.api import View, HGroup, Item
from traits.api import Instance, Bool, HasTraits, Tuple, Float
from enable.savage.trait_defs.ui.svg_button import SVGButton
from cns.widgets.icons import icons
import sys
import logging
log = logging.getLogger(__name__)

class PumpToolBar(ToolBar):
    '''
    Toolbar containing command buttons that allow us to control the pump via a
    GUI.  Three basic commands are provided: increase rate, decrease rate, and
    override the TTL input (so pump continuously infuses).
    '''

    kw               = dict(height=20, width=20, action=True)
    pump_override    = SVGButton('Run', filename=icons['right2'],
                                 tooltip='Override', toggle=True, **kw)
    pump_trigger     = SVGButton('Trigger', filename=icons['start'],
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
    iface_pump          = Instance('new_era.PumpInterface', ())
    pump_toggle         = Bool(False)
    pump_trigger_cache  = Tuple
    pump_volume_cache   = Float

    def monitor_pump(self):
        infused = self.iface_pump.get_infused(unit='ml')
        ts = self.get_ts()
        self.model.data.log_water(ts, infused)

    def pump_trigger(self, info=None):
        try:
            self.pump_refresh()
            self.iface_pump.run()
        except:
            log.error(sys.exc_info()[1])

    def pump_override(self, info=None):
        if not self.pump_toggle:
            self.pump_override_on()
        else:
            self.pump_override_off()

    def pump_override_on(self, info=None):
        if not self.pump_toggle:
            self.pump_refresh()
            self.pump_trigger_cache = self.iface_pump.get_trigger()
            self.pump_volume_cache = self.iface_pump.get_volume()
            self.iface_pump.set_volume(0)
            self.iface_pump.set_trigger('rising', None)
            self.iface_pump.run()
            self.pump_toggle = True

    def pump_override_off(self, info=None):
        if self.pump_toggle:
            self.iface_pump.stop()
            self.iface_pump.set_trigger(*self.pump_trigger_cache)
            self.iface_pump.set_volume(self.pump_volume_cache)
            self.pump_toggle = False

    def set_pump_volume(self, value):
        halted = self.iface_pump.get_status() == 'halted'
        if not halted: self.iface_pump.pause()
        self.iface_pump.set_volume(value, unit='ul')
        if not halted: self.iface_pump.resume()

    def set_pump_rate(self, value):
        halted = self.iface_pump.get_status() == 'halted'
        if not halted: self.iface_pump.pause()
        self.iface_pump.set_rate(value, unit='ml/min')
        if not halted: self.iface_pump.resume()

    def set_pump_syringe_diameter(self, value):
        halted = self.iface_pump.get_status() == 'halted'
        if not halted: self.iface_pump.pause()
        self.iface_pump.set_diameter(value, unit='mm')
        if not halted: self.iface_pump.resume()

    def set_pump_rate_delta(self, value):
        halted = self.iface_pump.get_status() == 'halted'
        if not halted: self.iface_pump.pause()
        self.current_pump_rate_delta = value
        if not halted: self.iface_pump.resume()

    def pump_refresh(self):
        self.set_pump_rate(self.get_current_value('pump_rate'))
        self.set_pump_volume(self.get_current_value('reward_volume'))

if __name__ == '__main__':
    PumpToolBar().configure_traits()

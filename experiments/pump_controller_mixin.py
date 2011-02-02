from cns.widgets.toolbar import ToolBar
from enthought.etsconfig.api import ETSConfig
from enthought.traits.ui.api import View, HGroup, Item, Controller, VGroup
from enthought.savage.traits.ui.svg_button import SVGButton
from enthought.traits.api import Instance, Bool, HasTraits, Button
from cns.widgets import icons

class PumpToolBar(ToolBar):
    '''
    Toolbar containing command buttons that allow us to control the pump via a
    GUI.  Three basic commands are provided: increase rate, decrease rate, and
    override the TTL input (so pump continuously infuses). 
    '''

    if ETSConfig.toolkit == 'qt4':
        kw               = dict(height=20, width=20, action=True)
        pump_increase    = SVGButton(filename=icons.up, tooltip='Increase rate',
                                     **kw)
        pump_decrease    = SVGButton(filename=icons.down, 
                                     tooltip='Decrease rate',**kw)
        pump_override    = SVGButton(filename=icons.right2, 
                                     tooltip='Override', toggle=True, **kw)
        pump_initialize  = SVGButton(filename=icons.start,
                                     tooltip='Initialize', **kw)
        pump_shutdown    = SVGButton(filename=icons.stop, tooltip='Shutdown',
                                     **kw)
        item_kw          = dict()
    else:
        pump_increase    = Button('+')
        pump_decrease    = Button('-')
        pump_override    = Button('O')
        pump_initialize  = Button('I')
        pump_shutdown    = Button('W')
        item_kw          = dict(width= -24, height= -24)

    traits_view = View(
            HGroup(Item('pump_override', **item_kw),
                   Item('pump_increase', **item_kw),
                   Item('pump_decrease', **item_kw),
                   enabled_when="object.handler.state<>'halted'",
                   show_labels=False,
                   ),
            #kind='subpanel'
            )

class PumpControllerMixin(HasTraits):

    pump_toolbar = Instance(PumpToolBar, (), toolbar=True)
    iface_pump = Instance('cns.equipment.new_era.PumpInterface', ())

    def monitor_pump(self):
        self.current_volume_dispensed = self.iface_pump.infused

    def init_pump(self, info=None):
        '''
        Initialize pump rate and syringe diameter
        '''
        self.set_pump_syringe_diameter(self.model.paradigm.pump_syringe_diameter)
        self.set_pump_rate(self.model.paradigm.pump_rate)
        self.set_pump_rate_delta(self.model.paradigm.pump_rate_delta)

    def pump_override(self, info):
        if self.iface_pump.trigger == 'run_high':
            self.iface_pump.run(trigger='start')
        else:
            self.iface_pump.run_if_TTL(trigger='run_high')

    def pump_increase(self, info):
        new_rate = self.iface_pump.rate + self.current_pump_rate_delta
        self.model.paradigm.pump_rate = new_rate
        self.apply_change(self.model.paradigm, 'pump_rate')

    def pump_decrease(self, info):
        new_rate = self.iface_pump.rate - self.current_pump_rate_delta
        self.model.paradigm.pump_rate = new_rate
        self.apply_change(self.model.paradigm, 'pump_rate')

    def set_pump_rate(self, value):
        self.iface_pump.rate = value

    def set_pump_syringe_diameter(self, value):
        self.iface_pump.diameter = value

    def set_pump_rate_delta(self, value):
        self.current_pump_rate_delta = value

if __name__ == '__main__':
    PumpToolBar().configure_traits()

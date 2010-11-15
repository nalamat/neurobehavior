from cns.widgets.toolbar import ToolBar
from enthought.etsconfig.api import ETSConfig
from enthought.traits.ui.api import View, HGroup, Item, Controller
from enthought.savage.traits.ui.svg_button import SVGButton
from enthought.traits.api import Instance, Bool, HasTraits
from cns.widgets import icons

class PumpToolBar(ToolBar):
    '''
    Toolbar containing command buttons that allow us to control the pump via a
    GUI.  Three basic commands are provided: increase rate, decrease rate, and
    override the TTL input (so pump continuously infuses). 
    '''

    if ETSConfig.toolkit == 'qt4':
        kw               = dict(height=24, width=24, action=True)
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
        item_kw          = dict(show_label=False)
    else:
        pump_increase    = Button('+')
        pump_decrease    = Button('-')
        pump_override    = Button('O')
        pump_initialize  = Button('I')
        pump_shutdown    = Button('W')
        item_kw          = dict(width= -24, height= -24, show_label=False)

    traits_view = View(
            HGroup(#Item('pump_initialize', 
                   #     enabled_when="object.handler.state=='halted'",
                   #     **item_kw),
                   #Item('pump_shutdown', 
                   #     enabled_when="object.handler.state=='halted'",
                   #     **item_kw),
                   Item('pump_override', 
                        enabled_when="object.handler.state<>'halted'",
                        **item_kw),
                   Item('pump_increase', **item_kw),
                   Item('pump_decrease', **item_kw),
                   ),
            kind='subpanel'
            )

class PumpControllerMixin(HasTraits):

    #pump_override_active = Bool
    pump_toolbar = Instance(PumpToolBar, (), toolbar=True)
    pump = Instance('cns.equipment.new_era.PumpInterface', ())

    def pump_override(self, info):
        if self.pump.trigger == 'run_high':
            self.pump.run(trigger='start')
            #self.pump_override_active = True
        else:
            self.pump.run_if_TTL(trigger='run_high')
            #self.pump_override = False

    def pump_increase(self, info):
        self.pump.rate += self.model.paradigm.pump_rate_delta

    def pump_decrease(self, info):
        self.pump.rate -= self.model.paradigm.pump_rate_delta

    def _apply_pump_rate(self, value):
        self.pump.rate = value

    def _apply_syringe_diameter(self, value):
        self.pump.diameter = value

if __name__ == '__main__':
    PumpToolBar().configure_traits()

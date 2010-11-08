from cns.widgets.toolbar import ToolBar
from enthought.etsconfig.api import ETSConfig
from enthought.traits.ui.api import View, HGroup, Item, Controller
from enthought.savage.traits.ui.svg_button import SVGButton
from enthought.traits.api import Instance, Bool
from cns.widgets import icons

#class PumpToolBar(ToolBar):
#    '''
#    Toolbar containing command buttons that allow us to control the pump via a
#    GUI.  Three basic commands are provided: increase rate, decrease rate, and
#    override the TTL input (so pump continuously infuses). 
#    '''
#
#    if ETSConfig.toolkit == 'qt4':
#        kw = dict(height=18, width=18, action=True)
#        increase = SVGButton(filename=icons.up, **kw)
#        decrease = SVGButton(filename=icons.down, **kw)
#        override = SVGButton(filename=icons.right2, tooltip='override',
#                             toggle=True, **kw)
#        item_kw = dict(show_label=False)
#    else:
#        increase = Button('+')
#        decrease = Button('-')
#        override = Button('O')
#        initialize = Button('I')
#        shutdown = Button('W')
#        item_kw = dict(width= -24, height= -24, show_label=False)
#
#    traits_view = View(
#            HGroup(Item('increase', **item_kw),
#                   Item('decrease', **item_kw),
#                   Item('override', **item_kw),
#                   '_',
#                   )
#            )

class PumpControllerMixin(Controller):

    #pump_override = Bool
    #pump_toolbar = Instance(PumpToolBar, ())
    pump = Instance('cns.equipment.new_era.PumpInterface', ())

    def pump_override(self, info):
        if self.iface.trigger == 'run_high':
            self.pump.run(trigger='start')
            self.pump_override = True
        else:
            self.pump.run_if_TTL(trigger='run_high')
            self.pump_override = False

    #def increase(self, info):
    #    pass

    def _apply_pump_rate(self, value):
        self.pump.rate = value

    def _apply_syringe_diameter(self, value):
        self.pump.diameter = value

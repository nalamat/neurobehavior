from enthought.traits.api import HasTraits, Float, Enum, Property
from enthought.traits.ui.api import View, Item, VGroup, HGroup

from cns import get_config

from eval import ExpressionTrait

SYRINGE_DATA = get_config('SYRINGE_DATA')

class PumpParadigmMixin(HasTraits):
    
    pump_rate = ExpressionTrait(0.5, label='Pump rate (ml/min)')
    pump_rate_delta = Float(0.025, label='Pump rate delta (ml)')
    pump_syringe = Enum(get_config('SYRINGE_DEFAULT'), 
                        sorted(SYRINGE_DATA.keys()),
                        store='attribute', ignore=True)
    pump_syringe_diameter = Property(store='attribute',
            depends_on='pump_syringe', queue=True, init=True)

    def _get_pump_syringe_diameter(self):
        return SYRINGE_DATA[self.pump_syringe]

    # Note that we have defined two views here, a simple view and a more
    # detailed view.  When including this mixin class, you can choose which view
    # is used.
    detailed_pump_settings = VGroup(
            HGroup(
                Item('pump_rate', label=u'Rate (mL/min)'),
                Item('pump_rate_delta', label=u'\u0394 Rate (mL/min)'),
                Item('tube_volume', label='Tube volume (mL)'),
                ),
            HGroup(
                Item('pump_syringe', label='Syringe'),
                Item('pump_syringe_diameter', label='Syringe diameter (mm)',
                    style='readonly'),
                ),
            label='Pump Settings', 
            show_border=True,
            )

    simple_pump_settings = VGroup(
            Item('pump_rate', label=u'Rate (mL/min)'),
            Item('pump_rate_delta', label=u'\u0394 Rate (mL/min)'),
            Item('pump_syringe', label='Syringe'),
            label='Pump Settings',
            show_border=True,
            )

    detailed_view = View(detailed_pump_settings)
    simple_view = View(simple_pump_settings)

if __name__ == '__main__':
    PumpSettingsMixin().configure_traits(view='simple_view')
    PumpSettingsMixin().configure_traits(view='detailed_view')

from enthought.traits.api import HasTraits, Float, Enum, Property
from enthought.traits.ui.api import View, Item, VGroup, HGroup

SYRINGE_DEFAULT = 'B-D 60cc (plastic)'
SYRINGE_DATA = {
        'B-D 10cc (plastic)': 14.43,
        'B-D 20cc (plastic)': 19.05,
        'B-D 30cc (plastic)': 21.59,
        'B-D 60cc (plastic)': 26.59,
        'Popper 20cc (glass)': 19.58,
        }

class PumpSettingsMixin(HasTraits):

    pump_rate = Float(0.5, store='attribute')
    #pump_rate_delta = Float(0.025, store='attribute')
    pump_syringe = Enum(SYRINGE_DEFAULT, sorted(SYRINGE_DATA.keys()),
                        store='attribute')
    syringe_diameter = Property(store='attribute', depends_on='pump_syringe')
    #tube_volume = Float(8.0, store='attribute')

    def _get_syringe_diameter(self):
        return SYRINGE_DATA[self.pump_syringe]

    detailed_pump_settings = VGroup(
            HGroup(
                Item('pump_rate', label=u'Rate (mL/min)'),
                Item('pump_rate_delta', label=u'\u0394 Rate (mL/min)'),
                Item('tube_volume', label='Tube volume (mL)'),
                ),
            HGroup(
                Item('pump_syringe', label='Syringe'),
                Item('syringe_diameter', label='Syringe diameter (mm)',
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

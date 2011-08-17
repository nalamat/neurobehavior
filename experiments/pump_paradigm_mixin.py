from enthought.traits.api import HasTraits, Float, Enum, Property, cached_property
from enthought.traits.ui.api import View, Item, VGroup, HGroup

from cns import get_config

from evaluate import Expression

SYRINGE_DATA = get_config('SYRINGE_DATA')

class PumpParadigmMixin(HasTraits):
    
    kw = {'context': True, 'store': 'attribute'}
    
    pump_rate = Expression(0.5, label='Pump rate (ml/min)', **kw)
    pump_rate_delta = Float(0.025, label='Pump rate delta (ml)', **kw)
    pump_syringe = Enum(get_config('SYRINGE_DEFAULT'), sorted(SYRINGE_DATA.keys()), 
                        label='Syringe', ignore=True, **kw)
    pump_syringe_diameter = Property(label='Syringe diameter (mm)', log=True,
            depends_on='pump_syringe', **kw)

    @cached_property
    def _get_pump_syringe_diameter(self):
        return SYRINGE_DATA[self.pump_syringe]

    # Note that we have defined two views here, a simple view and a more
    # detailed view.  When including this mixin class, you can choose which view
    # is used.
    detailed_pump_group = VGroup(
            HGroup(
                'pump_rate',
                'pump_rate_delta',
                ),
            HGroup(
                'pump_syringe',
                Item('pump_syringe_diameter', style='readonly'),
                ),
            label='Pump Settings', 
            show_border=True,
            )

    simple_pump_group = VGroup(
            'pump_rate',
            'pump_rate_delta',
            'pump_syringe',
            label='Pump Settings',
            show_border=True,
            )

    pump_paradigm_mixin_syringe_group = VGroup(
            Item('pump_syringe'),
            Item('pump_syringe_diameter', style='readonly'),
            label='Syringe',
            )

    detailed_view = View(detailed_pump_group)
    simple_view = View(simple_pump_group)

if __name__ == '__main__':
    PumpSettingsMixin().configure_traits(view='simple_view')
    PumpSettingsMixin().configure_traits(view='detailed_view')

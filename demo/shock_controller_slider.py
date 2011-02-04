'''
Created on Apr 29, 2010

@author: Brad
'''

from enthought.traits.api import *
from enthought.traits.ui.api import *
import operator as op
from cns.traits.ui.api import ListAsStringEditor

class ShockSettings(HasTraits):

    paradigm = Any
    shock = List
    dynamic_view = Property
    cache = Dict(Float, Float, {})

    get_tname = lambda self, x: ('shock_%f' % x).replace('.', '_')

    @on_trait_change('paradigm')
    def _paradigm_changed(self, new):
        for name in self.trait_names(shock=True):
            self.remove_trait(name)
        self.add_traits(new.pars)

    @on_trait_change('paradigm:pars[]')
    def _new_items(self, object, name, old, new):
        print object, name, old, new
        if old:
            self.remove_traits(old)
        if new:
            self.add_traits(new)

    def remove_traits(self, pars):
        for item in pars:
            tname = self.get_tname(item)
            self.remove_trait(tname)

    def add_traits(self, pars):
        for item in pars:
            tname = self.get_tname(item)
            label = '%r' % item
            meta = dict(low=0.0, high=5.0, default=0, shock=True, par=item, label=label)
            self.add_trait(tname, Range(**meta))
            try:
                level = self.cache[item]
            except KeyError:
                self.cache[item] = level = 0
            setattr(self, tname, level)
        self.trait_property_changed('dynamic_view', None, self.dynamic_view)

    def _get_dynamic_view(self):
        info = [(trait.par, name) for name, trait in self.traits(shock=True).items()]
        info.sort()
        return View(VGroup([t[1] for t in info],
                           label='Shock Level (V)',
                           show_border=True))

    @on_trait_change('+shock')
    def update_cache(self, name, new):
        self.cache[self.trait(name).par] = new

    def get_shock(self, par):
        return self.cache[par]

class Wrapper(HasTraits):

    pars = List
    settings = Instance(ShockSettings)

    traits_view = View(Item('pars', editor=ListAsStringEditor()),
                      Item('settings{}@',
                           editor=InstanceEditor(view_name='object.settings.dynamic_view')),
                           resizable=True)

class Test(HasTraits):
    #x = List(Float, [1, 2, 3])
    #traits_view = View(Item('x', editor=ListEditor(mutable=False, editor=RangeEditor(low=0, high=10))))
    class Setting(HasTraits):
        par = Float
        level = Range(0.0, 1, 0)
        traits_view = View('par', 'level', '-')

    x = List(Setting, [Setting(par=0.0, level=1), Setting(par=5, level=0.5)])
    #traits_view = View(Item('x', editor=ListEditor(editor=InstanceEditor())))
    traits_view = View(Item('x', editor=ListEditor(editor=InstanceEditor(), style='custom')))
    #traits_view = View(Item('x', editor=ListEditor(editor=TupleEditor(editors=[TextEditor(), RangeEditor()]))))


if __name__ == '__main__':
    Test().configure_traits()
    #Foo().configure_traits()
    #wr = Wrapper(pars=[1, 2, 3])
    #ss = ShockSettings(paradigm=wr)
    #wr.settings = ss
    #wr.configure_traits()
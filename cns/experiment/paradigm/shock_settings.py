'''I am no longer integrating ShockSettings into the paradigms that I build
since the Coulborn shocker does not appear to be reading the shock control.  In
addition, we are moving towards an air puff stimulus so it seems silly to put
any effort into getting ShockSettings to work and maintaining it.
'''
class ShockSettings(HasTraits):

    class Setting(HasTraits):
        par = Float
        level = Range(0.0, 1, 0)
        def __cmp__(self, other):
            if type(other) == type(self):
                return self.par-other.par
            else:
                return self.par-other
        def __hash__(self):
            return self.par.__hash__()
        def __repr__(self):
            return'Setting(par=%f, level=%f)' % (self.par, self.level)
        traits_view = View(['par{}~', 'level{}', '-'])

    paradigm = Any
    max_shock = Range(0.0, 5.0, 2.5, store='attribute')

    levels = List(Setting)
    #cache = Dict(Float, Setting, store='attribute')
    cache = Dict(Float, Float, store='attribute')
    
    def update(self):
        return
        #self.levels = []
        #self._add_pars(self.paradigm.pars)

    @on_trait_change('paradigm')
    def _paradigm_changed(self, new):
        self.update()

    @on_trait_change('paradigm:pars')
    def _new_items(self, object, name, old, new):
        return
        if old:
            for par in old:
                self.levels.remove(par)
        if new:
            self._add_pars(new)
            
    def _add_pars(self, pars):
        return
        for par in pars:
            level = self.cache.setdefault(par, 0)
            self.levels.append(self.Setting(par=par, level=level))
        self.levels.sort()

    def get_level(self, par):
        return 0
        #return self.cache[par]*self.max_shock

    editor = ListEditor(editor=InstanceEditor(), mutable=False, style='custom')
    traits_view = View([['max_shock{Maximum shock}'],
                        Item('levels{}', editor=editor), '|[Shock settings]'],
                       resizable=True)


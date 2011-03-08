'''
Created on May 20, 2010

@author: admin_behavior
'''
from enthought.traits.api import *
from enthought.traits.ui.api import *

def _to_list(string):
    separators = ';,'
    for s in separators:
        string = string.replace(s, ' ')
    value = [float(el) for el in string.split()]
    return value

def _to_string(list):
    return ', '.join([str(el) for el in list])

class ListAsStringEditor(TextEditor):

    evaluate = Callable(_to_list)
    format_func = Callable(_to_string)
    
class Settings(HasTraits):

    list = List
    levels = List
    
    class Setting(HasTraits):
        par = Float
        def __init__(self, par):
            HasTraits.__init__(self, par=par)
        def __cmp__(self, other):
            return self.par == other

    @on_trait_change('list')
    def _new_items(self, object, name, old, new):
        if old:
            for par in old:
                self.levels.remove(par)
        if new:
            for par in new:
                self.levels.append(par)
            
    editor = ListEditor(editor=InstanceEditor(), mutable=False, style='custom')
    traits_view = View([Item('list', editor=ListAsStringEditor()),
                        Item('levels{}', editor=editor), '|[Settings]'],
                       resizable=True)

if __name__ == '__main__':
    Settings().configure_traits()
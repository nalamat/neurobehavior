'''
Created on May 4, 2010

@author: admin_behavior
'''
from enthought.traits.api import HasTraits, List, Float
from enthought.traits.ui.api import View, Item
from cns.traits.ui.api import ListAsStringEditor

class Parameters(HasTraits):

    parameters = List(Float, [1, 2, 3, 4])
    view = View(Item('parameters', editor=ListAsStringEditor()))

if __name__ == '__main__':
    x = ListAsStringEditor()
    pars = Parameters()
    print 'Before editing:', pars.parameters
    pars.configure_traits()
    print 'After editing: ', pars.parameters

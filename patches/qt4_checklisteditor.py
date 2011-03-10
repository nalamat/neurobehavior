'''
Created on Jun 21, 2010

@author: admin_behavior
'''

import os
os.environ['ETS_TOOLKIT'] = 'qt4'

from enthought.traits.api import *
from enthought.traits.ui.api import *

class Test(HasTraits):
    x = List(editor=CheckListEditor(name='y'))
    y = List(['a', 'b', 'c', 'd', 'e'])

Test().configure_traits()
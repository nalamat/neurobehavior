'''
Created on May 4, 2010

@author: admin_behavior
'''

from enthought.traits.api import Callable
from enthought.traits.ui.api import TextEditor

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
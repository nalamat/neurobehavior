'''
Created on Jul 20, 2010

@author: Brad
'''
import numpy as np
import re
import tables
import logging
from datetime import datetime

log = logging.getLogger(__name__)

name_lookup = {'group':     'Group',
               'earray':    'EArray',
               'array':     'Array',
               'table':     'Table'}

def node_keys(node):
    attrs = node._v_attrs._f_list('user')
    attrs = set(attrs) - set(['module', 'klass'])
    return list(attrs)

def node_items(node):
    attrs = node_keys(node)
    values = [node._v_attrs[attr] for attr in attrs]
    return attrs, values

def rgetattr_or_none(obj, attr):
    try:
        return rgetattr(obj, attr)
    except AttributeError:
        return None

def get_or_append_node(node, name, type='group', *arg, **kw):
    try:
        # TODO: add type checking?
        return getattr(node, name)
    except tables.NoSuchNodeError:
        return append_node(node, name, type, *arg, **kw)

def append_node(node, name, type='group', *arg, **kw):
    log.debug('appending %r to node %r', name, node._v_pathname)
    file = node._v_file
    path = node._v_pathname
    type = name_lookup[type.lower()]
    func = getattr(file, 'create' + type)
    new_node = func(path, name, *arg, **kw)
    #file.flush()
    return new_node

time_fmt = '%Y_%m_%d_%H_%M_%S'

def extract_date_from_name(node, pre='date', post=''):
    name = node._v_name
    string = re.sub('^'+pre, '', name)
    string = re.sub(post+'$', '', string)
    return datetime.strptime(string, time_fmt)
    
def append_date_node(node, pre='date', post='', type='group', *arg, **kw):
    name = pre + datetime.now().strftime(time_fmt) + post
    return append_node(node, name, type, *arg, **kw)

def _v_getattr(obj, extended_attr, strict=False):
    if extended_attr == '':
        return obj
    if not strict and not hasattr(obj, extended_attr):
        obj = getattr(obj, '_v_attrs')
    return getattr(obj, extended_attr)

def rgetattr(obj, extended_attr, strict=False):
    if '.' in extended_attr:
        base, extended_attr = extended_attr.split('.', 1)
        if base == '':
            base = '_v_parent'
        obj = _v_getattr(obj, base, strict)
        return rgetattr(obj, extended_attr, strict)
    else:
        return _v_getattr(obj, extended_attr, strict)

def node_match(n, filter):
    '''Checks for match against each keyword.  If an attribute is missing or
    any match fails, returns False.

    Filter must be a dictionary
    '''

    for extended_attr, v in filter.items():
        try:
            value = rgetattr(n, extended_attr)
        except AttributeError:
            return False

        # Check to see if last value returned is a match
        if type(v) == type(''):
            try:
                if re.match(v, value) is None:
                    return False
            except TypeError:
                # TypeError will be raised if value is not a string or buffer
                return False
        else:
            if v != value:
                return False
    return True

def _walk(where, filter, mode):
    '''Recursively returns all nodes hanging off of the starting node that match
    the given criteria.

    Criteria can be specified as keyword arguments where the keyword indicates
    the attribute.  The keyword can either be one of the node's special
    attributes (e.g. _v_pathname or _v_name) or a user-set attribute.  The value
    may be a regular expression as well.

    Hint, to limit to a given depth, use the _v_depth attribute (you may have to
    account for the starting depth, not sure as I have never used this feature).
    Obviously this is a moot point with the non-recursive version.

    Returns
    -------
    iterable

    For a non-recursive version, see :func:`list_nodes`.  Use the non-recursive
    version where possible (e.g. when you are interested only in the immediate
    children) as it will be much faster. 

    To return all nodes with the attribute klass='Animal'
    >>> fh = tables.openFile('example_data.h5', 'r')
    >>> animal_nodes = list(walk_nodes(fh.root, {'_v_attrs.klass': 'Animal'}))

    To return all nodes who have a subnode, data, with the attribute
    klass='RawAversiveData*'
    >>> fh = tables.openFile('example_data.h5', 'r')
    >>> base_node = fh.root.Cohort_0.animals.Animal_0.experiments
    >>> filter = {'data.klass: 'RawAversiveData*'}
    >>> experiment_nodes = [n for n in walk_nodes(base_node, filter)]

    To return all nodes whose name matches a given pattern
    >>> fh = tables.openFile('example_data.h5', 'r')
    >>> filter = {'_v_name': '^Animal_\d+'}
    >>> animal_nodes = [n for n in walk_nodes(fh.root, filter)]
    '''
    for node in getattr(where, mode)():
        if node_match(node, filter):
            yield node

from functools import partial

walk_nodes = partial(_walk, mode='_f_walkNodes')
iter_nodes = partial(_walk, mode='_f_iterNodes')

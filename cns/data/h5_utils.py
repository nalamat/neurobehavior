'''
Created on Jul 20, 2010

@author: Brad
'''
import tables
import datetime
import logging
log = logging.getLogger(__name__)

name_lookup = {'group':     'Group',
               'earray':    'EArray',
               'array':     'Array',
               'table':     'Table'}

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

def append_date_node(node, pre='date', post='', type='group', *arg, **kw):
    name = pre + datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S') + post
    return append_node(node, name, type, *arg, **kw)

def walk_nodes(start, **kw):
    '''Return all nodes hanging off of the starting node, using keyword
    arguments as an attribute filter.

    Currently supports strings that end in a wildcard (e.g. if you version your
    class names with _v0_2, etc. then the wildcard can ignore those).

    TODO: improve wildcard support

    To return all nodes with the attribute klass='Animal'
    >>> fh = tables.openFile('filename.h5', 'r')
    >>> animal_nodes = walk_nodes(fh.root, klass='Animal')
    '''
    def match(n, kw):
        attrs = node._v_attrs
        for k, v in kw.items():
            if k not in attrs:
                return False
            elif v.endswith('*') and not attrs[k].startswith(v.strip('*')):
                return False
            elif attrs[k]!=v:
                return False
        return True
    return [node for node in start._f_walkNodes() if match(node, kw)]

'''
Created on Jul 20, 2010

@author: Brad
'''

# Before you can understand how the code works, you need to understand a little
# about how the HDF5 data structure is represented in Python.  PyTables has a
# really nice API (application programming interface) that we can use to access
# the "nodes" of the table.  First, open a 'handle' to the file.
# >>> fh = tables.openFile('filename', 'r')
# The top-level node can be accessed via an attribute called root
# >>> root = fh.root
# A child node can be accessed via it's name
# >>> animal = fh.root.Cohort_0.animals.Animal_0
# The properties of the animal are stored in a special "node" called _v_attrs
# (this is a PyTables-specific feature, other HDF5 libraries may have different
# methods for accessing the attribute).
# >>> nyu_id = fh.root.Cohort_0.animals.Animal_0._v_attrs.nyu_id

import numpy as np
import re
import tables
import logging
from datetime import datetime
from rec import flatten_recarray
from matplotlib import mlab

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

    for extended_attr, criterion in filter.items():
        try:
            value = rgetattr_or_none(n, extended_attr)
            if not criterion(value):
                return False
        except AttributeError:
            return False
        except TypeError:
            if not (value == criterion):
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

def extract_data(input_files, filters, fields=None):
    # Gather all the data nodes by looking for the nodes in the HDF5 tree that
    # match our filter.  Nodes are HDF5 objects (e.g. either a group containing
    # children objects (Animal.experiments contains multiple experiments) or a
    # table (e.g. the par_info table).  The function walk_nodes is a special
    # function I wrote that interates through every node in the HDF5 file and
    # examins its metadata.  A list of all the nodes whose metadata matches the
    # filter properties are returned.
    nodes = []
    for file_name in input_files:
        file = tables.openFile(file_name, 'r')
        nodes.extend(n for n in walk_nodes(file.root, filter=filters))

    if fields is not None:
        # The user has requested that we add additional attributes to the data
        # we are extracting.
        new_attrs = []
        new_names = []
        for field in fields:
            attr, name = field
            value = rgetattr_or_none(nodes[0], attr)
            if isinstance(value, tables.Node):
                # Let's investigate these attributes to see if they point to a
                # node with multiple attributes (e.g. if the attribute path
                # points to an animal node, it will have multiple attributes
                # including birth, sex and identifier).  If it is a node with
                # multiple attributes, ensure that we harvest all of these
                # attributes.  These attributes can be accessed from the node
                # via _v_attrs.
                user_attrs = node_keys(value)
                new_attrs.extend(attr + '_v_attrs.' + a for a in user_attrs)
                new_names.extend(name + '.' + a for a in user_attrs)
            else:
                # The attribute path points directly to a single attribute, not
                # a node.  How boring.
                new_attrs.append(attr)
                new_names.append(name)

        # set() is a special datatype that ensures that all items in the list
        # are unique.  By converting our list to a set, then back, we can be
        # guaranteed that our new list has only unique items.
        fields = sorted(set(zip(new_attrs, new_names)))
        attrs, names = zip(*fields)

    # Now that we have gathered the nodes, walk through them to extract the
    # information we need.
    if type(nodes[0]) == tables.Table:
        # Node is a HDF5 table.  Table.read() returns a Numpy record array (a
        # very powerful data structure that is essentially an array with named
        # columns and nested data structures).
        data_records = []
        for node in nodes:
            # Some HDF5 tables are nested (e.g. they have tables within tables).
            # A lot of the functions we are going to be using don't deal well
            # with nested recarrays, so we are simply going to "flatten" the
            # nested structure.
            d = flatten_recarray(node.read())
            if fields is not None:
                # rgetattr (i.e. "recursive get attribute") is a special
                # function I wrote that can recursively traverse the object
                # hierarchy and return the value of the given attribute.  A '.'
                # tells rgetattr to go to the parent of the current node.  For
                # example, assume that node is
                # animal.experiments.experiment.data.  If we want to get the
                # value stored in animal.nyu_id (three levels up), we would use
                # the string '...nyu_id'.
                extra_data = [rgetattr_or_none(node, attr) for attr in attrs]
                d = mlab.rec_append_fields(d, names, extra_data)

            # There are sometimes datatype inconsistencies between "versions" of
            # the date (e.g. I may have defined a variable as type integer in
            # the behavior program, then changed my mind and defined it as a
            # float in a later version).  We cannot concatenate record arrays
            # that have slightly different datatypes.  However, Numpy offers a
            # very powerful function called fromrecords that automatically
            # coerces fields (i.e. columns) in the records to a common datatype
            # when creating the record array.  We extract a list of the records
            # in the array (using the tolist() function).  
            for e in d.tolist():
                print len(e)
            data_records.extend(d.tolist())

        # Now that we have a list of all the records, let's make the final
        # record array so we can easily run computations across the dataset.

        return np.rec.fromrecords(data_records, names=d.dtype.names)
    else:
        # Since I sometimes add and remove items from the data structure, not
        # all nodes will have the exact same attributes.  Let's iterate through
        # all of the nodes and get a list of attributes for each node.
        node_attrs = []
        node_names = []
        for node in nodes:
            user_attrs = node_keys(node)
            node_attrs.extend('_v_attrs.' + a for a in user_attrs)
            node_names.extend(user_attrs)
        node_fields = sorted(set(zip(node_attrs, node_names)))
        node_attrs, node_names = zip(*node_fields)

        if fields is not None:
            node_attrs = list(node_attrs)
            node_names = list(node_names)
            node_attrs.extend(attrs)
            node_names.extend(names)

        # Now that we have a list of all the attributes we should attempt to
        # extract, let's loop through the nodes and extract the values.
        arrs = {}
        for node in nodes:
            for attr, name in zip(node_attrs, node_names):
                # Since we are aware not all attributes are present, we'll set
                # the value to None if it is missing
                value = rgetattr_or_none(node, attr)
                arrs.setdefault(name, []).append(value)
        return np.rec.fromarrays(arrs.values(), names=arrs.keys())


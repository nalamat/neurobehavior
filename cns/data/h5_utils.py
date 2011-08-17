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

def get_temp_file():
    from cns import get_config
    filename = join(get_config('TEMP_ROOT'), 'test_experiment.hd5')
    datafile = tables.openFile(filename, 'w')
    return datafile

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
time_pattern = re.compile(r'\d{4}_(\d{2}_?){5}')

def extract_date_from_string(string):
    time_string = time_pattern.search(string).group()
    return datetime.strptime(time_string, time_fmt)

def extract_date_from_name(node, pre=None, post=None):
    if pre is not None or post is not None:
        raise DeprecationWarning, "pre and post are no longer used"
    time_string = time_pattern.find(node._v_name).group()
    return datetime.strptime(time_string, time_fmt)

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
    '''
    Checks for match against each keyword.  If an attribute is missing or any
    match fails, returns False.

    Filter can be a dictionary or list of tuples.  If the order in which the
    filters are applied is important, then provide a list of tuples.
    '''
    # If filter is a dictionary, convert it to a sequence of tuples
    if type(filter) == type({}):
        filter = tuple((k, v) for k, v in filter.items())

    # If user only provided one filter rather than a sequence of filters,
    # convert it to a sequence of length 1 so the following loop can handle it
    # better
    if len(filter[0]) == 1:
        filter = (filter,)

    for extended_attr, criterion in filter:
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
    '''
    Starting at the specifide node, `walk_nodes` visits each node in the
    hierarchy, returning a list of all nodes that match the filter criteria.

    Filters are specified as a sequence of tuples, (attribute, filter).  As
    each node is visited, each filter is called with the corresponding value of
    its attribute.  The node is discarded if it is missing one or more of the
    filter attributes.

    Each filter may be a callable that returns a value or raises an exception.
    If the filter raises an exception or returns an object whose truth value
    is Fales, the node is discarded.

    Attributes may be specified relative to the nodes of interest using the '.'
    separator.

    Attribute examples:

        _v_name
            Name of the current node
        ._v_name
            Name of the parent node
        .._v_name
            Name of the grandparent node
        paradigm.bandwidth
            Value of the bandwidth attribute on the child node named 'paradigm'
        .paradigm.bandwidth
            Value of the bandwidth attribute on the sibling node named
            'paradigm' (i.e. check to see if the parent of the current node has
            a child node named 'paradigm' and get the value of bandwidth
            attribute on this child node).

    If you have ever worked with pathnames via the command line, you may
    recognize the '.' separator as a homologue of the directory separator '../'.
    Using this analogy, '..paradigm.bandwidth' translates to
    '../../paradigm/bandwidth' and '._v_name' translates to '../_v_name'.

    Filter examples:

        ('_v_name', re.compile('^\d+.*').match) 
        Matches all nodes whose name begins with a sequence of numbers

        ('_v_name', 'par_info')
        Matches all nodes whose name is exactly 'par_info'

        ('..start_time', lambda x: (strptime(x).date()-date.today()).days <= 7)
        Matches all nodes whose grandparent (two levels up) contains an
        attribute, start_time, that evaluates to a date that is within the last
        week.  Useful for restricting your analysis to data collected recently.

    Valuable node attributes:

        _v_name
            Name of the node
        _v_pathname
            HDF5 pathname of the node
        _v_depth
            Depth of the node relative to the root node (root node depth is 0)

    If all of the attributes are found for the given node and the attribute
    values meet the filter criterion, the node is added to the list.

    To return all nodes with the attribute klass='Animal'
    >>> fh = tables.openFile('example_data.h5', 'r')
    >>> filter = ('_v_attrs.klass', 'Animal')
    >>> iterator = walk_nodes(fh.root, filter)
    >>> animal_nodes = list(iterator)

    To return all nodes who have a subnode, data, with the attribute 'klass'
    whose value is a string beginning with 'RawAversiveData'.
    >>> fh = tables.openFile('example_data.h5', 'r')
    >>> base_node = fh.root.Cohort_0.animals.Animal_0.experiments
    >>> filter = ('data.klass', re.compile('RawAversiveData.*').match)
    >>> experiment_nodes = list(walk_nodes(base_node, filter))

    To return all nodes whose name matches a given pattern
    >>> fh = tables.openFile('example_data.h5', 'r')
    >>> filter = ('_v_name', re.compile('^Animal_\d+').match)
    >>> animal_nodes = list(walk_nodes(fh.root, filter))
    '''
    for node in getattr(where, mode)():
        if node_match(node, filter):
            yield node

from functools import partial

walk_nodes = partial(_walk, mode='_f_walkNodes')
iter_nodes = partial(_walk, mode='_f_iterNodes')

def extract_data(input_files, filters, fields=None):
    '''
    Extracts the data you want into a record array, flattening the HDF5
    hierarchy in the process.  This results in what is, essentially, a
    denormalized table. 

    Parameters
    ----------
    input_files : list
        A list of HDF5 files to extract data from
    filters : sequence of tuples
        Each tuple contains two elements, an attribute name and a filter. The
        value of the attribute is extracted from the node being in.  The filter
        must be sufficiently strict that it only matches one object type or
        table type.  Don't try to "merge" par_info with trial_log.  It won't
        work.  The tables that match the filter are then concatenated.
    fields : 
        Extra metadata to append (as columns) to the tables extracted by the
        filter.

    Typical HDF5 file structure
    ---------------------------
    Cohort_{number}
        _v_attrs
            description
        animals
            Animal_{number}
                _v_attrs
                    nyu_id
                    identifier (e.g. tail, fluffy)
                    parents
                    birth
                    sex
                experiments
                    PositiveDTExperiment_{date_time}
                        _v_attrs
                            start_time
                            stop_time
                            date
                            duration
                        data
                            _v_attrs
                                clip
                                nogo_trial_count
                                go_trial_count
                                OBJECT_VERSION (incremented when format changes)
                            contact
                                poke_TTL
                                    _v_attrs
                                        fs (sampling frequency)
                                spout_TTL
                                    _v_attrs
                                        fs (sampling frequency)
                                {et cetera}
                            par_info
                            trial_log
                            water_log
                            {et cetera}
                        paradigm
                            _v_attrs
                                {list of all relevant paradigm attributes}

    For convenience, '_v_attrs' is typically implied (e.g. if the node does not
    have a child with the given name, _v_attrs is checked to see if it contains
    the requested attribute name).  If the node has both a child and an
    attribute with the same name (rare), then you need to prepend the attribute
    name with '_v_attrs.' when you want to obtain the attribute name.

    Given the following hierarchy

        experiment
            _v_attrs
                start_date
                start_time
                data
            data
            paradigm

    When requesting 'start_date', '_v_attrs.start_date' is returned since the
    experiment node does not have a child node named 'start_date'.  However,
    requesting 'data' returns the child node, data.  If you want the data
    attribute, you must explicitly request '_v_attrs.data'.
    
    Give the following arugments:

        filters = (('_v_name', 'trial_log'),)
        fields  = (('....identifier', 'id'),
                   ('....sex', 'sex'))

    With a HDF5 file containing following structure:

        Animal_0
            _v_attrs
                identifier = Fluffy
                sex = M
            experiments
                Experiment
                    _v_attrs
                        start_time
                        end_time
                        duration
                    data
                        trial_log (parameter, trial_type, response)
                            parameter_1, trial_type_1, response_1
                            parameter_2, trial_type_2, response_2
                            parameter_3, trial_type_3, response_3
                            parameter_4, trial_type_4, response_4
                            parameter_5, trial_type_5, response_5
                        contact
                            poke_TTL
                            spout_TTL
                            ...
                    paradigm
        Animal_1
            _v_attrs
                identifier = Tail
                sex = F
            experiments
                Experiment
                    _v_attrs
                        start_time
                        end_time
                        duration
                    data
                        trial_log (parameter, trial_type, response)
                            parameter_1, trial_type_1, response_1
                            parameter_2, trial_type_2, response_2
                            parameter_3, trial_type_3, response_3
                            parameter_4, trial_type_4, response_4
                            parameter_5, trial_type_5, response_5
                        contact
                            poke_TTL
                            spout_TTL
                            ...
                    paradigm

    The result will be a record array containing the following named columns:

        id,         sex, parameter,     trial_type,   response

    With the following records:

        Fluffy,     M,   parameter_1,   trial_type_1, response_1
        Fluffy,     M,   parameter_2,   trial_type_2, response_2
        Fluffy,     M,   parameter_3,   trial_type_3, response_3
        Fluffy,     M,   parameter_4,   trial_type_4, response_4
        Fluffy,     M,   parameter_5,   trial_type_5, response_5
        Tail,       F,   parameter_1,   trial_type_1, response_1
        Tail,       F,   parameter_2,   trial_type_2, response_2
        Tail,       F,   parameter_3,   trial_type_3, response_3
        Tail,       F,   parameter_4,   trial_type_4, response_4
        Tail,       F,   parameter_5,   trial_type_5, response_5

    Once extracted, these records can be indexed by column name and row:

    >>> print data['sex']
    ['M', 'M', 'M', 'M', 'M', 'F', 'F', 'F', 'F', 'F']

    >>> print data[:3]['parameter']
    [parameter_1, parameter_2, parameter_3]

    >>> mask = data['parameter'] == parameter_1
    >>> print data[mask][['id', 'trial_type']]
    [['Fluffy', trial_type_1],
     ['Tail',   trial_type_1]]
    '''

    # Gather all the data nodes by looking for the nodes in the HDF5 tree that
    # match our filter.  Nodes are HDF5 objects (e.g. either a group containing
    # children objects (Animal.experiments contains multiple experiments) or a
    # table (e.g. the par_info table).  The function walk_nodes is a special
    # function I wrote that interates through every node in the HDF5 file and
    # examins its metadata.  A list of all the nodes whose metadata matches the
    # filter properties are returned.
    nodes = []
    for file_name in input_files:
        with tables.openFile(file_name, 'r') as file:
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

    if len(nodes) == 0:
        return []

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
            data_records.extend(d.tolist())

        # Now that we have a list of all the records, let's make the final
        # record array so we can easily run computations across the dataset.

        data = np.rec.fromrecords(data_records, names=d.dtype.names)
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
        data = np.rec.fromarrays(arrs.values(), names=arrs.keys())
    return data

def create_date_filter(start, end, extract=False):
    if extract:
        return lambda d: start <= extract_date_from_string(d) < end
    return lambda d: start <= d < end

def find_ancestor(node, filter):
    '''
    Find the nearest ancestor that matches the given filter
    '''
    ancestor = node._v_parent
    if node_match(ancestor, filter):
        return ancestor
    else:
        return find_ancestor(ancestor, filter)

def find_ancestor_attr(node, attr):
    ancestor = node._v_parent
    if attr in ancestor._v_attrs._f_list('user'):
        return ancestor._v_attrs[attr]
    else:
        return find_ancestor_attr(ancestor, attr)

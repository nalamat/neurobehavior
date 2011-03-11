'''
Usage examples

Extract the history of your experiments
>>> h5extract.py -n paradigm -a ...=animal,._v_name=exp_name *.cohort.hd5 test.csv
>>> h5extract.py -n positivedtdata -a ....=animal,._v_name=exp_name *.cohort.hd5 test.csv


'''
import sys
sys.path.append('c:/users/brad/workspace/neurobehavior')
from cns.data.h5_utils import (walk_nodes, rgetattr, node_keys, node_items,
                               rgetattr_or_none)
from cns.data.rec import flatten_recarray
import tables
import numpy as np
from matplotlib import mlab

from pylab import *

def cluster(r, groupby):
    rowd = dict()
    for i, row in enumerate(r):
        key = tuple([row[attr] for attr in groupby])
        rowd.setdefault(key, []).append(i)
    keys = rowd.keys()
    keys.sort()
    return keys, rowd

common_nodes = {
    'paradigm': { '_v_name': 'paradigm' },
    'par_info': { '.klass': 'PositiveDTData', '_v_name': 'par_info' },
    'animals':  { 'klass': 'Animal' },
    }

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

def extract_table(input_files, output_file, filters, fields=None):
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
            value = rgetattr(nodes[0], attr)
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

    # Finally, save the data to a file
    mlab.rec2csv(data, output_file)

if __name__ == '__main__':
    # This code is simply "argument parsing" code that formats command line
    # arguments into a structure that's easy for my script to use.  The argparse
    # library has very robust error handling and type-checking of the arguments,
    # so I don't need to worry about sanitizing the user input.

    to_dict = lambda args: dict(item.split('=') for item in args.split(','))
    lookup_filter = lambda arg: common_nodes[arg]

    from argparse import ArgumentParser, Action, FileType

    class FilterAction(Action):
        def __call__(self, parser, namespace, values, option_string=None):
            key = values.split()[0]
            setattr(namespace, self.dest, common_nodes[key])

    class AttributeAction(Action):
        def __call__(self, parser, namespace, values, option_string=None):
            string = values.split()[0]
            names = []
            attrs = []
            for value in values.split(','):
                if '=' in value:
                    attr, name = value.split('=')
                else:
                    name = attr = value
                names.append(name)
                attrs.append(attr)
            setattr(namespace, self.dest, zip(attrs, names))

    parser = ArgumentParser(description='Dump data to table')
    parser.add_argument('files', help='Input files', nargs='+')
    parser.add_argument('output', type=FileType('wb'), help='Output file')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-f', '--filter', type=to_dict, help='Filter to apply')
    group.add_argument('-n', '--node', type=str, dest='filter',
                       choices=common_nodes.keys(), action=FilterAction,
                       help='Node to extract')
    parser.add_argument('-a', '--annotate', type=str, default=None,
                        action=AttributeAction,
                        help='Extra metadata to add to output')
    args = parser.parse_args()
    extract_table(args.files, args.output, args.filter, args.annotate)

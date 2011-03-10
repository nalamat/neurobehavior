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
    'animals': { 'klass': 'Animal' },
    }

def extract_table(input_files, output_file, filters, fields=None):
    # Gather all the data nodes by looking for the nodes in the HDF5 tree that
    # match our filter.
    nodes = []
    for file_name in input_files:
        file = tables.openFile(file_name, 'r')
        nodes.extend(n for n in walk_nodes(file.root, filter=filters))

    if fields is not None:
        # Checking to see if we requested a node as an attribute
        new_attrs = []
        new_names = []
        for field in fields:
            attr, name = field
            value = rgetattr(nodes[0], attr)
            if isinstance(value, tables.Node):
                user_attrs = node_keys(value)
                new_attrs.extend(attr + '_v_attrs.' + a for a in user_attrs)
                new_names.extend(name + '.' + a for a in user_attrs)
            else:
                new_attrs.append(attr)
                new_names.append(name)
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
                # rgetattr is a special function I wrote that can recursively
                # traverse the object hierarchy and return the value of the
                # given attribute.  A lone '.' tells rgetattr to go to the
                # parent of the current node.  The node hierarchy is
                # animal.experiments.experiment.data.  Given the data node
                # (which we obtained above), we want to get the value stored in
                # animal._v_attrs.nyu_id (three levels up).  The appropriate
                # search string is '..._v_attrs.nyu_id'.
                extra_data = [rgetattr_or_none(node, attr) for attr in attrs]
                d = mlab.rec_append_fields(d, names, extra_data)

            # There are sometimes datatype inconsistencies between "versions" of
            # the date (e.g. I may have defined a variable as type integer in
            # the behavior program, then changed my mind and defined it as a
            # float in a later version).  We cannot concatenate record arrays
            # that have slightly different datatypes.  However, Numpy offers a
            # very powerful function called fromrecords that automatically
            # coerces fields to a common datatype.  We maintain a list of all
            # the records found during the extraction process.
            data_records.extend(d.tolist())

        # Concatenate all of this data into a single big record array so that we
        # can easily run computations across the dataset.
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

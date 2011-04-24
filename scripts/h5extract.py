'''
Usage examples

Extract the history of your experiments
>>> h5extract.py -n paradigm -a ...=animal,._v_name=exp_name *.cohort.hd5 test.csv
>>> h5extract.py -n positivedtdata -a ....=animal,._v_name=exp_name *.cohort.hd5 test.csv

'''
import sys
sys.path.append('c:/users/brad/workspace/neurobehavior')
from cns.data.h5_utils import (walk_nodes, rgetattr, node_keys, node_items,
                               rgetattr_or_none, extract_data)
from cns.data.rec import flatten_recarray
import tables
import numpy as np
from matplotlib import mlab

from pylab import *

common_nodes = {
    'paradigm': { '_v_name': 'paradigm' },
    'par_info': { '_v_name': 'par_info' },
    'trial_log': { '_v_name': 'trial_log'},
    'animal': { 'klass': 'Animal' },
    }

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

    # Extract the data
    data = extract_data(args.files, args.filter, args.annotate)
    mlab.rec2csv(data, args.output)

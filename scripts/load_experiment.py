#!python

import os

# Ensure that ETS toolkit will default to PyQt4 and use the PyQt (instead of
# the less stable PySide backend) if we load it
os.environ['ETS_TOOLKIT'] = 'qt4'

# This is very important since there's a memory leak when using PySide.  This
# has been fixed in the latest revision of enable; however, it
# probably will not appear until a version of ETS > 7.2-2.
os.environ['QT_API'] = 'pyqt'

# IMPORTANT!  Do not import any portion of the Neurobehavior code (e.g. cns,
# experiments, paradigms, etc. until after the comment indicating it is safe to
# do so in the code below.
import os
import sys
import argparse
import logging
import logging.config
from os import path
from time import strftime
from datetime import datetime
import threading
import tables as tb
import pandas
from cns.widgets.file_handler import get_save_file, get_directory

def configure_logging(filename, filename2):
    time_format = '[%(asctime)s] :: %(name)s - %(levelname)s - %(message)s'
    simple_format = '%(name)s - %(levelname)s - %(message)s'

    logging_config = {
            'version': 1,
            'formatters': {
                'time': { 'format': time_format },
                'simple': { 'format': simple_format },
                },
            'handlers': {
                # This is what gets printed out to the console
                'console': {
                    'class': 'logging.StreamHandler',
                    'formatter': 'simple',
                    'level': 'DEBUG',
                    },
                # This is what gets saved to the file
                'file': {
                    'class': 'logging.FileHandler',
                    'formatter': 'time',
                    'filename': filename,
                    'level': 'DEBUG',
                    },
                },
            # This is where you would change the logging level of specific modules.
            # This is very helpful when you are trying to debug a very specific
            # module and want to turn off the messages from other modules.
            'loggers': {
                # This module complains if you pass zero-length data to it for
                # plotting.  However, we initialize the plots with zero-length data
                # in the beginning of the experiment since we don't have any trials
                # yet.  Let's silence this module.
                'chaco.barplot': { 'level': 'CRITICAL', },
                'experiments': { 'level': 'DEBUG' },
                'paradigms': { 'level': 'DEBUG' },
                'cns': { 'level': 'DEBUG' },
                'cns.chaco_exts': { 'level': 'INFO' },
                'cns.channel': { 'level': 'INFO' },
                'tdt': { 'level': 'INFO' },
                'new_era': { 'level': 'DEBUG' },
                },
            'root': {
                'handlers': ['console', 'file'],
                },
            }

    if filename2 is not None:
        logging_config['handlers']['file2'] = {
                'class': 'logging.FileHandler',
                'formatter': 'time',
                'filename': filename2,
                'level': 'DEBUG',
                }
        logging_config['root']['handlers'].append('file2')

    logging.config.dictConfig(logging_config)

class VerifyUniqueParameters(argparse.Action):

    def __call__(self, parser, args, values, option_string=None):
        if len(set(values)) != len(values):
            mesg = 'Parameter list cannot contain duplicates'
            raise argparse.ArgumentTypeError(mesg)
        else:
            setattr(args, self.dest, values)

class VerifyCalibration(argparse.Action):

    def __call__(self, parser, args, values, option_string=None):
        for filename in values:
            if not path.isfile(filename):
                mesg = '{} must be a file'
                raise argparse.ArgumentTypeError(mesg.format(filename))
        setattr(args, self.dest, values)

class VerifyServer(argparse.Action):

    def __call__(self, parser, args, value, option_string=None):
        host, port = value.split(':')
        setattr(args, self.dest, (host, int(port)))

def do_monkeypatch():
    # List of class methods that need to be monkey-patched. This is not an
    # exhaustive list. We can add to this as we find more methods that we want
    # to use.
    monkeypatch = [
        tb.File._gettitle,
        tb.File._settitle,
        tb.File._deltitle,
        tb.File._getfilters,
        tb.File._setfilters,
        tb.File._delfilters,
        tb.File.create_group,
        tb.File.create_table,
        tb.File.create_array,
        tb.File.create_carray,
        tb.File.create_earray,
        tb.File.create_vlarray,
        tb.File.create_hard_link,
        tb.File.create_soft_link,
        tb.File.create_external_link,
        tb.File.rename_node,
        tb.File.move_node,
        tb.File.copy_node,
        tb.File.remove_node,
        tb.File.get_node_attr,
        tb.File.set_node_attr,
        tb.File.del_node_attr,
        tb.File.copy_node_attrs,
        tb.File.copy_children,
        tb.File.copy_file,
        tb.File.list_nodes,
        tb.File.iter_nodes,
        tb.File.mark,
        tb.File.undo,
        tb.File.redo,
        tb.File.goto,
        tb.File.flush,
        tb.File.close,
        tb.File.set_node_attr,
        tb.File.list_nodes,
        tb.Table.append,
        tb.Table.modify_rows,
        tb.Table.read,
        tb.Table._g_create,
        tb.Table._g_open,
        tb.Table._get_column_instance,
        tb.Table._disable_indexing_in_queries,
        tb.Table._enable_indexing_in_queries,
        tb.Table.will_query_use_indexing,
        tb.Table.where,
        tb.Table.read_where,
        tb.Table.append_where,
        tb.Table.get_where_list,
        tb.Table.itersequence,
        tb.Table._check_sortby_csi,
        tb.Table.itersorted,
        tb.Table.read_sorted,
        tb.Table.iterrows,
        tb.Table.get_enum,
        tb.Table.col,
        tb.Table.__getitem__,
        tb.Table.__setitem__,
        tb.Table.modify_coordinates,
        tb.Table.modify_column,
        tb.Table.modify_columns,
        tb.Table.flush_rows_to_index,
        tb.Table.remove_rows,
        tb.Table.remove_row,
        tb.Table.reindex,
        tb.Table.reindex_dirty,
        tb.Table.copy,
        tb.Array._g_create,
        tb.Array.iterrows,
        tb.Array.next,
        tb.Array.__getitem__,
        tb.Array.__setitem__,
        tb.Array._read,
        # tb.Array._read_slice,
        # tb.Array._read_coords,
        # tb.Array._read_selection,
        tb.Array._write_slice,
        tb.Array._write_coords,
        tb.Array._write_selection,
        tb.Array._getnrows,
        tb.Array._getrowsize,
        tb.EArray.append,
        tb.EArray.set_attr,
        tb.EArray.read,
        tb.EArray.__setitem__,
        tb.EArray.__getitem__,
        tb.EArray.__len__,
        tb.Node._f_getattr,
        tb.Node._f_setattr,
        tb.Node._f_delattr,
        tb.Node._f_move,
        # tb.Node._g_set_location,
        # tb.Node._g_del_location,
        tb.file.NodeManager.rename_node,
        # tb.file.NodeManager.drop_from_cache,
        tb.file.NodeManager.drop_node,
        tb.file.NodeManager.flush_nodes,
        # tb.file.NodeManager.shutdown,
        # tb.attributeset.AttributeSet.__getattr__,
        # tb.attributeset.AttributeSet._g__setattr,
        tb.attributeset.AttributeSet._g__delattr,
        tb.attributeset.AttributeSet._g_update_node_location,
        # pandas.DataFrame.append,
        # pandas.core.indexing._iLocIndexer.__getitem__,
    ]

    def secure_lock(f, lock):
        def wrapper(*args, **kwargs):
            with lock:
                return f(*args, **kwargs)

        return wrapper

    lock = threading.Lock()
    for im in monkeypatch:
        wrapped_im = secure_lock(im, lock)
        setattr(im.im_class, im.im_func.func_name, wrapped_im)

    def table_length(self):
        with lock:
            return self.nrows
    setattr(tb.Table, 'length', property(table_length))


CALIBRATION_HELP = '''Path to file containing calibration data for {} speaker.
If this option is not specified, the most recent calibration file available
will be used for the experiment.'''

FILE_HELP = '''File to store current experiment to'''

LIB_ROOT_HELP = '''Although virtualenv is recommended as the best tool for
managing stable and developmental verisons of Neurobehavior on a single
computer, programmers coming from Matlab tend to prefer the approach of creating
a copy of the program to a new folder each time and having the program update
the system path based on its current directory.  This option is not throughly
tested.  Use at your own risk.'''

SERVER_HELP = '''TDT RPC server address (in the format hostname:port).  For
example, localhost:3333 or regina.cns.nyu.edu:3333.'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Launch experiment")

    parser.add_argument('type', type=str,
                        help='The type of experiment to launch')

    parser.add_argument('-r', '--rove', help='Parameter(s) to rove',
                        nargs='+', action=VerifyUniqueParameters, default=[],
                        required=False)
    parser.add_argument('-a', '--analyze', help='Parameter(s) to analyze',
                        nargs='+', action=VerifyUniqueParameters, default=[])
    parser.add_argument('--repeats',
                        help='Specify number of repeats for each trial setting',
                        action='store_true', default=False)

    #debug_choices = ['regular', 'verbose', 'annoying', 'obnoxious']
    parser.add_argument('--debug', action='store_true',
                        help='Prevents some exceptions from being silenced')

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-p', '--profile', dest='mode', action='store_const',
                       const='profile', default='regular',
                       help='Profile experiment')
    group.add_argument('--memory', dest='mode', action='store_const',
                       const='memory', default='regular',
                       help='Graph memory usage')
    group.add_argument('-t', '--test', dest='mode', action='store_const',
                       const='test', help='Test experiment')
    group.add_argument('-i', '--inspect', dest='mode', action='store_const',
                       const='inspect', help='Print available parameters')
    group.add_argument('-f', '--file', type=str, help="File to save data to")
    group.add_argument('-of', '--open-file', dest='open_file',
                       action='store', const='', default=None, type=str, nargs='?',
                       help="Open file dialog for saving data")
    group.add_argument('-d', '--directory', dest='directory',
                       action='store', default=None, type=str,
                       help="Directory for saving animal data")
    group.add_argument('-od', '--open-directory', dest='open_directory',
                       action='store', const='', default=None, type=str, nargs='?',
                       help="Open directory dialog for saving animal data")

    parser.add_argument('-n', '--neural', dest='physiology',
                        action='store_true', help='Acquire neurophysiology',
                        default=False)
    parser.add_argument('--nopump', action='store_true', help='Deactivate pump',
                        default=False)
    parser.add_argument('--sim', action='store_true', help='Simulation mode',
                        default=False)

    parser.add_argument('--save-microphone', action='store_true',
            help='Save microphone data?', default=False)

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--cal', action=VerifyCalibration, nargs=2, default=None,
            help='Calibration files to use for primary and secondary speaker')
    group.add_argument('--att', action='store_true',
            help='Treat signal level as an attenuation value')
    parser.add_argument('--equalized', action='store_true',
            help='Use equalized calibration?', default=False)

    args = parser.parse_args()

    if args.debug:
        # By default, exceptions that occur in the trait change handlers (i.e.
        # the callback functions) are silenced.  When debugging, it's often
        # helpful for these exceptions to propagate into the main thread so we
        # can identify the source of the issue.
        from traits.api import push_exception_handler
        push_exception_handler(reraise_exceptions=True)

    from experiments import loader
    from cns import get_config

    # Configure the logging
    log_root      = get_config('LOG_ROOT')
    time_fmt      = get_config('TIME_FORMAT')
    timestr       = datetime.now().strftime(time_fmt)
    log_filename2 = None
    if path.exists(log_root):
        log_filename = path.join(log_root, timestr + '.log')
    else:
        import tempfile
        import warnings
        import textwrap
        fh = tempfile.NamedTemporaryFile(delete=False)
        log_filename = fh.name
        mesg = '''
        The folder for storing log files, {}, does not exist.  the log file will be
        saved to the temporary file {}.  In the future, please create the folder,
        {}, or update your NEUROBEHAVIOR_SETTINGS and/or NEUROBEHAVIOR_BASE to point
        to the appropriate log file directory.'''
        mesg = mesg.format(log_root, log_filename, log_root)
        warnings.warn(textwrap.dedent(mesg).replace('\n', ''))

    try:
        # Do some additional checking of argument list to make sure it is valid
        if args.mode != 'inspect':
            invalid = loader.get_invalid_parameters(args)
            if len(invalid) != 0:
                if len(invalid) == 1:
                    mesg = ' is an invalid parameter'
                else:
                    mesg = ' are invalid parameters'
                sys.exit(', '.join(invalid) + mesg)

        do_monkeypatch()

        args.animal = None

        if args.open_directory is not None:
            args.directory = get_directory(args.open_directory)
            if args.directory is None:
                raise ValueError('No directory was selected')
            print 'Selected directory ', args.directory
            # Fall into args.directory if statement

        if args.directory is not None:
            if not os.path.isdir(args.directory):
                os.makedirs(args.directory)
            args.animal   = os.path.basename(args.directory)
            node_name     = loader.get_experiment(args.type).node_name
            name          = '_'.join([args.animal, node_name, timestr])
            args.file     = os.path.join(args.directory, name + '.h5')
            log_filename2 = os.path.join(args.directory, name + '.log')
            print 'Will save data to ', args.file
            # Fall into args.file if statement

        if args.open_file is not None:
            args.file = get_save_file(args.open_file, 'HDF5 Files (*.h5;*.hdf5)|*.h5;*.hdf5')
            if args.file is None:
                raise ValueError('No file was selected')
            print 'Selected file ', args.file
            # Fall into args.file if statement

        configure_logging(log_filename, log_filename2)

        ###############################################################################
        # Everything after this point will get stored to the log file
        ###############################################################################

        # Finally, do the requested action
        if args.file is not None:
            loader.launch_experiment(args, args.file)
        elif args.mode == 'profile':
            loader.profile_experiment(args)
        elif args.mode == 'test':
            loader.test_experiment(args)
        elif args.mode == 'inspect':
            loader.inspect_experiment(args)
        elif args.mode == 'memory':
            loader.objgraph_experiment(args)
        else:
            loader.launch_experiment_selector(args)

    except Exception, e:
        from os import isatty
        import sys, traceback
        traceback.print_exc(file=sys.stdout)

        # Now, if we are running from a terminal, don't exit until the user hits
        # enter so they have time to read the error message (if the terminal is
        # launched via a Windows shortcut, then it often closes before the user
        # can read the message).  Note that the error message will be logged to
        # the file as well (assuming you've configured the levels properly).
        if isatty(sys.stdout.fileno()):
            raw_input("Hit enter to exit")

    finally:
        print "Log file saved to", log_filename

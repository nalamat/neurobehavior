#!python

import sys
import argparse
import logging
import logging.config
from time import strftime
from os import path
time_format = '[%(asctime)s] :: %(name)s - %(levelname)s - %(message)s'
simple_format = '%(name)s - %(levelname)s - %(message)s'

# Set up the logging file.  If a path has been defined, save the file to that
# path.  If not, save the logging data to a temporary file.
from cns import get_config

log_root = get_config('LOG_ROOT') 
if path.exists(log_root):
    filename = path.join(log_root, strftime('%Y%m%d_%H%M.log'))
else:
    import tempfile
    import warnings
    import textwrap
    fh = tempfile.NamedTemporaryFile(delete=False)
    filename = fh.name
    mesg = '''
    The folder for storing log files, {}, does not exist.  the log file will be
    saved to the temporary file {}.  In the future, please create the folder,
    {}, or update your NEUROBEHAVIOR_SETTINGS and/or NEUROBEHAVIOR_BASE to point
    to the appropriate log file directory.'''
    mesg = mesg.format(log_root, filename, log_root)
    warnings.warn(textwrap.dedent(mesg).replace('\n', ''))

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
                'level': 'WARNING',
                }
            },
        # This is where you would change the logging level of specific modules.
        # This is very helpful when you are trying to debug a very specific
        # module and want to turn off the messages from other modules.
        'loggers': {
            # This module complains if you pass zero-length data to it for
            # plotting.  However, we initialize the plots with zero-length data
            # in the beginning of the experiment since we don't have any trials
            # yet.  Let's silence this module.
            'enthought.chaco.barplot': { 'level': 'CRITICAL', },
            'experiments': { 'level': 'DEBUG' },
            'paradigms': { 'level': 'DEBUG' },
            'tdt': { 'level': 'INFO' },
            'cns': { 'level': 'WARN' },
            'cns.data': { 'level': 'DEBUG' },
            'neurogen': { 'level': 'WARN' },
            },
        'root': {
            'handlers': ['console', 'file'],
            },
        }

logging.config.dictConfig(logging_config)
log = logging.getLogger()

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
example, localhost:13131 or regina.cns.nyu.edu:13131.'''

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

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-p', '--profile', dest='mode', action='store_const',
                       const='profile', default='regular', 
                       help='Profile experiment') 
    group.add_argument('-t', '--test', dest='mode', action='store_const',
                       const='test', help='Test experiment') 
    group.add_argument('-i', '--inspect', dest='mode', action='store_const',
                       const='inspect', help='Print available parameters')
    group.add_argument('-f', '--file', type=str, help="File to save data to")

    parser.add_argument('-n', '--neural', dest='physiology',
                        action='store_true', help='Acquire neurophysiology',
                        default=False)
    parser.add_argument('--address', help=SERVER_HELP, action=VerifyServer)

    #parser.add_argument('--paradigm', help='Paradigm settings file to load')
    #parser.add_argument('--physiology', help='Physiology settings file to load')

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--cal', action=VerifyCalibration, nargs=2, default=None,
            help='Calibration files to use for primary and secondary speaker')
    group.add_argument('--att', action='store_true', 
            help='Treat signal level as an attenuation value')
    parser.add_argument('--equalized', action='store_true',
            help='Use equalized calibration?', default=False)

    parser.add_argument('--modify-path', action='store_true',
            dest='modify_path', default=False, help=LIB_ROOT_HELP)

    args = parser.parse_args()

    if args.modify_path:
        from os.path import join, dirname, abspath, normpath
        from glob import glob
        search_string = join(dirname(__file__), '../../*/setup.py')
        for module_path in glob(search_string):
            module_path = normpath(abspath(dirname(module_path)))
            sys.path.insert(0, module_path)
            print "Added {} to the Python path".format(module_path)

    try:
        # Since we may be modifying the path to point to a development version
        # of neurobehavior rather than the default that is installed (via the
        # --modify-path command line flag), we need to wait to import the
        # experiment loader until the path has been updated.
        from experiments import loader

        # Do some additional checking of argument list to make sure it is valid
        if args.mode != 'inspect':
            invalid = loader.get_invalid_parameters(args)
            if len(invalid) != 0:
                if len(invalid) == 1:
                    mesg = ' is an invalid parameter'
                else:
                    mesg = ' are invalid parameters'
                sys.exit(', '.join(invalid) + mesg)

        # Finally, do the requested action
        if args.file is not None:
            loader.launch_experiment(args, args.file)
        elif args.mode == 'profile':
            loader.profile_experiment(args)
        elif args.mode == 'test':
            loader.test_experiment(args)
        elif args.mode == 'inspect':
            loader.inspect_experiment(args)
        else:
            loader.launch_experiment_selector(args)

    except Exception, e:
        from os import isatty
        import sys, traceback
        traceback.print_exc(file=sys.stdout)

        # Now, if we are running from a terminal, don't exit until the user hits
        # enter so they have time to read the error message.  Note that the
        # error message will be properly logged as well.
        if isatty(sys.stdout.fileno()):
            raw_input("Hit enter to exit")

    finally:
        print "Log file saved to ", filename

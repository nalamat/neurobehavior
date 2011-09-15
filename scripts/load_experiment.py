#!python

import sys
import argparse
import logging
log = logging.getLogger()

class VerifyUniqueParameters(argparse.Action):

    def __call__(self, parser, args, values, option_string=None):
        if len(set(values)) != len(values):
            sys.exit('Parameter list cannot contain duplicates')
        else:
            setattr(args, self.dest, values)
            
CALIBRATION_HELP = '''Path to file containing calibration data for {} speaker.
If this option is not specified, the most recent calibration file available
will be used for the experiment.'''

FILE_HELP = '''File to store current experiment to'''

LIB_ROOT_HELP = '''Although virtualenv is recommended as the best tool for
managing stable and developmental verisons of Neurobehavior on a single
computer, less programmers coming from Matlab tend to prefer the approach of
creating a copy of the program to a new folder each time and having the program
update the system path (e.g. Matlab-style) based on its current directory.  This
option is not supported.  Use at your own risk.'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Launch experiment")

    parser.add_argument('type', type=str, 
                        help='The type of experiment to launch')

    parser.add_argument('-r', '--rove', help='Parameter(s) to rove',
                        nargs='+', action=VerifyUniqueParameters, default=[])
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
    group.add_argument('-f', '--file', type=str)

    parser.add_argument('-n', '--neural', dest='physiology',
                        action='store_true', help='Acquire neurophysiology',
                        default=False)
    parser.add_argument('-s', '--server', help='Hardware server',
                        default='localhost:13013')
    
    parser.add_argument('-c1', dest='calibration_1',
                        help=CALIBRATION_HELP.format('primary'))
    parser.add_argument('-c2', dest='calibration_2',
                        help=CALIBRATION_HELP.format('secondary'))

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
        log.exception(e)
        # Now, if we are running from a terminal, don't exit until the user hits
        # enter so they have time to read the error message.  Note that the
        # error message will be properly logged as well.
        if isatty(sys.stdout.fileno()):
            raw_input("Hit enter to exit")

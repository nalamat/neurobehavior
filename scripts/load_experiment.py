#!python

import os 
import sys
from experiments import loader
import argparse
import tempfile

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

    args = parser.parse_args()

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
        log.exception(e)
        # Now, if we are running from a terminal, don't exit until the user hits
        # enter so they have time to read the error message.  Note that the
        # error message will be properly logged as well.
        if os.isatty(sys.stdout.fileno()):
            raw_input("Hit enter to exit")

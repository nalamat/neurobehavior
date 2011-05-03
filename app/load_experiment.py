import sys
import settings
from experiments import loader
import argparse

class VerifyUniqueParameters(argparse.Action):

    def __call__(self, parser, args, values, option_string=None):
        if len(set(values)) != len(values):
            sys.exit('Parameter list cannot contain duplicates')
        else:
            setattr(args, self.dest, values)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Launch experiment")

    parser.add_argument('type', type=str, choices=loader.EXPERIMENTS.keys(),
                        help='The type of experiment to launch')

    parser.add_argument('-r', '--rove', help='Parameter(s) to rove',
                        nargs='+', action=VerifyUniqueParameters, default=[])
    parser.add_argument('-a', '--analyze', help='Parameter(s) to analyze',
                        nargs='+', action=VerifyUniqueParameters, default=[])

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-p', '--profile', dest='mode', action='store_const',
                       const='profile', default='regular', 
                       help='Profile experiment') 
    group.add_argument('-t', '--test', dest='mode', action='store_const',
                       const='test', help='Test experiment') 
    group.add_argument('-i', '--inspect', dest='mode', action='store_const',
                       const='inspect', help='Print available parameters')

    parser.add_argument('-n', '--neural', dest='physiology',
                        action='store_true', help='Acquire neurophysiology',
                        default=False)
    parser.add_argument('-s', '--subprocess', dest='subprocess',
                        action='store_true', help='Run TDT IO in a subprocess')

    args = parser.parse_args()

    import cns
    cns.RCX_USE_SUBPROCESS = args.subprocess
    print args

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
    if args.mode == 'profile':
        loader.profile_experiment(args)
    elif args.mode == 'test':
        loader.test_experiment(args)
    elif args.mode == 'inspect':
        loader.inspect_experiment(args)
    else:
        loader.launch_experiment(args)

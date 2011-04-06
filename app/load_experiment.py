import sys
import settings
from experiments.loader import (launch_experiment, profile_experiment,
        test_experiment, EXPERIMENTS)
import argparse

from enthought.traits.api import HasTraits, Enum, Bool, Trait
from enthought.traits.ui.api import View, VGroup, Item

class Options(HasTraits):
    
    type = Enum(EXPERIMENTS.keys())
    mode = Enum('regular', 'profile', 'test') 
    subprocess = Bool(False)
    physiology = Bool(False)

    traits_view = View(
            VGroup(
                Item('type', label='Experiment type'),
                Item('mode'),
                Item('subprocess', label='Run device IO in subprocess?'),
                Item('physiology', label='Acquire neural data?')
                ),
            buttons=['OK', 'Cancel'],
            )

if __name__ == '__main__':
    if len(sys.argv) == 1:
        args = Options()
        if not args.configure_traits():
            sys.exit()
    else:
        parser = argparse.ArgumentParser(description="Launch experiment")
        parser.add_argument('type', type=str, choices=EXPERIMENTS.keys(),
                help='The type of experiment to launch')
        group = parser.add_mutually_exclusive_group()
        group.add_argument('-p', '--profile', dest='mode', action='store_const',
                const='profile', default='regular', help='Profile experiment') 
        group.add_argument('-t', '--test', dest='mode', action='store_const',
                const='test', help='Test experiment') 
        parser.add_argument('-n', '--neural', dest='physiology',
                action='store_true', help='Acquire neurophysiology',
                default=False)
        parser.add_argument('-s', '--subprocess', dest='subprocess',
                action='store_true', help='Run TDT IO in a subprocess')
        parser.add_argument('-v', '--variables', dest='variables',
                help='Vary these parameters')
        args = parser.parse_args()

    import cns
    cns.RCX_USE_SUBPROCESS = args.subprocess

    if args.mode == 'profile':
        profile_experiment(args.type, args.physiology)
    elif args.mode == 'test':
        test_experiment(args.type, args.physiology)
    else:
        launch_experiment(args.type, args.physiology)

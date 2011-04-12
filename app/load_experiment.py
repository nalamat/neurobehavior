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
        parser.add_argument('parameters', type=str, help='Parameters to use',
                nargs='+')
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
        args = parser.parse_args()

    import cns
    cns.RCX_USE_SUBPROCESS = args.subprocess

    # We need to configure the TrialSetting object to contain the correct
    # parameters
    from experiments.trial_setting import TrialSetting, trial_setting_editor
    from enthought.traits.api import Float
    from enthought.traits.ui.api import ObjectColumn
    columns = []
    for parameter in args.parameters:
        TrialSetting.add_class_trait(parameter, Float)
        column = ObjectColumn(name=parameter, label=parameter, width=75)
        columns.append(column)
    TrialSetting.parameters = args.parameters
    trial_setting_editor.columns = columns

    if args.mode == 'profile':
        profile_experiment(args)
    elif args.mode == 'test':
        test_experiment(args)
    else:
        launch_experiment(args)

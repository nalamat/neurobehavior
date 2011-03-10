if __name__ == '__main__':
    import settings
    from experiments.loader import (launch_experiment, profile_experiment,
            test_experiment, EXPERIMENTS)
    import argparse

    parser = argparse.ArgumentParser(description="Launch experiment")
    parser.add_argument('type', type=str, nargs=1, choices=EXPERIMENTS.keys(),
                        help='The type of experiment to launch')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-p', '--profile', dest='profile', action='store_true',
                       help='Profile experiment') 
    group.add_argument('-t', '--test', dest='test', action='store_true',
                       help='Test experiment') 
    parser.add_argument('-n', '--neural', dest='physiology',
                        action='store_true', help='Acquire neurophysiology')
    args = parser.parse_args()

    if args.profile:
        profile_experiment(args.type[0], args.physiology)
    elif args.test:
        test_experiment(args.type[0], args.physiology)
    else:
        launch_experiment(args.type[0], args.physiology)

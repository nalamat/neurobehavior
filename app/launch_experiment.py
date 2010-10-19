if __name__ == '__main__':
    from config import settings
    import sys
    from cns import experiment
    experiments = experiment.experiment_map.keys()

    # First item in sys.argv list is the name of the program.  When called from
    # the command line as python launch_experiment.py aversiveFM, sys.argv will
    # be a list: ['launch_experiment', 'aversiveFM']
    if len(sys.argv) == 2 and sys.argv[1] in experiments:
            experiment.load_experiment_launcher(sys.argv[1])
    else:
        exp_options = ', '.join(experiments)
        usage = 'launch_experiment: missing or incorrect experiment type'
        usage += '\nExperiment type can be one of %s.' % exp_options
        sys.stdout.write(usage)

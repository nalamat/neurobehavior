if __name__ == '__main__':
    import settings
    from cns import experiment
    import logging
    logging.root.warn('this is working?')
    experiment.load_experiment_launcher()

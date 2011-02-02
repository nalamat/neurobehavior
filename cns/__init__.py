from os.path import dirname, join, abspath

LIBRARY_ROOT = dirname(abspath(__file__)) # not sure if this is still used
DATA_ROOT = 'C:/experiments/data'   # where data files should be stored
LOG_ROOT = 'C:/experiments/logs'    # where log files should be st ored
TEMP_ROOT = 'C:/experiments/temp'   # location for temporary files
COHORT_PATH = DATA_ROOT # i.e. store the cohort data files here

# not used (was toying with the idea of saving a paradigm)
PAR_WILDCARD    = 'Paradigm files (*.paradigm)|*.paradigm|'
# extension for cohort files
COHORT_WILDCARD = 'Cohort files (*.cohort.hd5)|*.cohort.hd5|'

if __name__ == '__main__':
    # When you first install Neurobehavior on a new computer, you need to create
    # the appropriate folders for saving the data and related information.  To
    # make this happen, type:
    # >>> python -m cns.__init__
    from os import makedirs
    for path in (DATA_ROOT, TEMP_ROOT, LOG_ROOT):
        try:
            makedirs(path)
        except OSError:
            print "Unable to make directory %s, check to see if it exists" % \
                  path

import os
from os.path import dirname, join, abspath

BASE_DIRECTORIES = {
        'REGINA'    : 'E:/',
        'DFNKWCH1'  : 'C:/EXPERIMENTS',
        'SEMPLE'    : None,
        'ROSEN'     : None,
        }

BASE_DIRECTORY = BASE_DIRECTORIES[os.getenv('COMPUTERNAME')]
LOG_ROOT    = join(BASE_DIRECTORY, 'logs') # where log files should be stored
TEMP_ROOT   = join(BASE_DIRECTORY, 'temp') # location for temporary files
DATA_ROOT   = join(BASE_DIRECTORY, 'data') # location for data files
COHORT_PATH = DATA_ROOT                    # location for cohort files

# extension to use for cohort files
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

import os
from os.path import dirname, join, abspath

BASE_DIRECTORIES = {
        'REGINA'        : 'E:/',            # In 1016
        'DFNKWCH1'      : 'C:/EXPERIMENTS', # In 1012
        'SEMPLE'        : None,
        'ROSENLAB'      : 'C:/EXPERIMENTS',
        'PHOENIX-NYU'   : 'C:/users/brad/workspace/neurobehavior_base',
        }

BASE_DIRECTORY = BASE_DIRECTORIES[os.getenv('COMPUTERNAME')]
LOG_ROOT    = join(BASE_DIRECTORY, 'logs') # where log files should be stored
TEMP_ROOT   = join(BASE_DIRECTORY, 'temp') # location for temporary files
DATA_ROOT   = join(BASE_DIRECTORY, 'data') # location for data files
COHORT_PATH = DATA_ROOT                    # location for cohort files

# __file__ is a special variable that is available in all Python files (when
# loaded by the Python interpreter) that contains the file path.  We extract the
# directory portion of the path and use that to determine where the RCX files
# are stored.
RCX_PATH = join(abspath(dirname(__file__), '../components')

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
